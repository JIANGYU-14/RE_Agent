from fastapi import APIRouter, Depends
from typing import List, Dict, Any

from app.repositories.messages_repo import MessagesRepo
from app.core.db import get_engine

router = APIRouter()

def get_messages_repo() -> MessagesRepo:
    return MessagesRepo(get_engine())

@router.get("/sessions/{session_id}/messages")
def history(
    session_id: str,
    messages_repo: MessagesRepo = Depends(get_messages_repo)
):
    messages = messages_repo.list_messages(session_id)
    return {"session_id": session_id, "messages": messages}
