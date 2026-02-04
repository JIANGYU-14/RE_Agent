from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import asyncio
import json
import os
import re
import requests

from app.core.agentkit_client import AgentKitClient
from app.repositories.messages_repo import MessagesRepo
from app.repositories.sessions_repo import SessionsRepo
from app.core.db import get_engine
from app.services.session_title import async_generate


router = APIRouter()
agent = AgentKitClient()

def split_text(text: str, max_chars: int) -> List[str]:
    if max_chars <= 0 or len(text) <= max_chars:
        return [text]

    tokens = re.findall(r"\S+\s*", text)
    if not tokens:
        return [text[i : i + max_chars] for i in range(0, len(text), max_chars)]

    parts: List[str] = []
    buf = ""
    for token in tokens:
        if not buf:
            buf = token
            continue

        if len(buf) + len(token) <= max_chars:
            buf += token
        else:
            parts.append(buf)
            buf = token

    if buf:
        parts.append(buf)

    final_parts: List[str] = []
    for part in parts:
        if len(part) <= max_chars:
            final_parts.append(part)
            continue
        final_parts.extend(part[i : i + max_chars] for i in range(0, len(part), max_chars))

    return final_parts


# ---------- request / response models ----------

class ChatRequest(BaseModel):
    session_id: str
    text: str
    use_public_paper: bool = False


class ChatResponse(BaseModel):
    answer: str
    parts: List[Dict[str, Any]]


# ---------- dependencies ----------

def get_messages_repo() -> MessagesRepo:
    return MessagesRepo(get_engine())


def get_sessions_repo() -> SessionsRepo:
    return SessionsRepo(get_engine())


# ---------- api ----------

@router.post("/chat")
async def chat(
    payload: ChatRequest,
    messages_repo: MessagesRepo = Depends(get_messages_repo),
    sessions_repo: SessionsRepo = Depends(get_sessions_repo),
):
    session_id = payload.session_id
    user_text = payload.text

    session = sessions_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")
    if session.get("status") != "active":
        raise HTTPException(status_code=409, detail="session is not active")

    # 1️⃣ save user message
    messages_repo.save_message(
        session_id=session_id,
        role="user",
        parts=[
            {
                "type": "text",
                "content": user_text,
            }
        ],
    )

    sessions_repo.touch_session(session_id)

    async def event_generator():
        full_answer = ""
        max_chars = int(os.getenv("CHAT_STREAM_CHUNK_SIZE", "16"))
        base_delay_ms = int(os.getenv("CHAT_STREAM_CHUNK_DELAY_MS", "25"))
        punct_delay_ms = int(os.getenv("CHAT_STREAM_PUNCT_DELAY_MS", "80"))
        punct_chars = set("。！？!?；;.\n")
        try:
            async for chunk in agent.astream_chat(
                session_id=session_id,
                text=user_text,
                use_public_paper=payload.use_public_paper,
            ):
                if chunk.get("type") == "text":
                    content = chunk.get("content", "")
                    for part in split_text(content, max_chars):
                        out_chunk = dict(chunk)
                        out_chunk["content"] = part
                        yield f"data: {json.dumps(out_chunk)}\n\n"
                        full_answer += part
                        if base_delay_ms > 0:
                            delay_seconds = base_delay_ms / 1000.0
                            if punct_delay_ms > 0 and part and part[-1] in punct_chars:
                                delay_seconds += punct_delay_ms / 1000.0
                            delay_seconds = min(delay_seconds, 0.2)
                            await asyncio.sleep(delay_seconds)
                elif chunk.get("type") == "error":
                    yield f"data: {json.dumps(chunk)}\n\n"
                    full_answer += f"\n[Error: {chunk.get('content')}]"
                else:
                    yield f"data: {json.dumps(chunk)}\n\n"

            # Save assistant message after stream ends
            if full_answer:
                assistant_parts = [
                    {
                        "type": "text",
                        "content": full_answer,
                        "metadata": None,
                    }
                ]
                messages_repo.save_message(
                    session_id=session_id,
                    role="assistant",
                    parts=assistant_parts,
                )
                sessions_repo.touch_session(session_id)
                async_generate(session_id)

        except Exception as e:
            error_msg = f"Stream error: {str(e)}"
            yield f"data: {json.dumps({'type': 'error', 'content': error_msg})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
