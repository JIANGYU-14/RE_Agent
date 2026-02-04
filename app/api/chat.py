from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
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
        stream_chunk_size_raw = os.getenv("CHAT_STREAM_CHUNK_SIZE", "16")
        try:
            stream_chunk_size = int(stream_chunk_size_raw)
        except ValueError:
            stream_chunk_size = 16

        if stream_chunk_size <= 0:
            stream_chunk_size = 16

        def split_text(text: str) -> list[str]:
            if not text:
                return []
            tokens = re.findall(r"\S+\s*", text)
            if not tokens:
                tokens = [text]
            chunks: list[str] = []
            current = ""
            for token in tokens:
                if len(token) > stream_chunk_size:
                    if current:
                        chunks.append(current)
                        current = ""
                    for i in range(0, len(token), stream_chunk_size):
                        piece = token[i : i + stream_chunk_size]
                        if piece:
                            chunks.append(piece)
                    continue
                if current and len(current) + len(token) > stream_chunk_size:
                    chunks.append(current)
                    current = token
                else:
                    current += token
            if current:
                chunks.append(current)
            return chunks

        try:
            async for chunk in agent.astream_chat(
                session_id=session_id,
                text=user_text,
                use_public_paper=payload.use_public_paper,
            ):
                if chunk.get("type") == "text":
                    content = chunk.get("content")
                    if isinstance(content, str):
                        full_answer += content
                        for piece in split_text(content):
                            piece_payload = {**chunk, "content": piece}
                            yield f"data: {json.dumps(piece_payload)}\n\n"
                        continue
                elif chunk.get("type") == "error":
                    full_answer += f"\n[Error: {chunk.get('content')}]"
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

    return StreamingResponse(event_generator(), media_type="text/event-stream")
