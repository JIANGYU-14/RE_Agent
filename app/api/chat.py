from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import json
import os
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
        try:
            async for chunk in agent.astream_chat(
                session_id=session_id,
                text=user_text,
                use_public_paper=payload.use_public_paper,
            ):
                # Forward chunk to client
                yield f"data: {json.dumps(chunk)}\n\n"
                
                # Accumulate text for storage
                if chunk.get("type") == "text":
                    full_answer += chunk.get("content", "")
                elif chunk.get("type") == "error":
                    # Handle error in stream
                    full_answer += f"\n[Error: {chunk.get('content')}]"
            
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
