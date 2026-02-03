from fastapi import APIRouter, Depends, HTTPException

from app.repositories.messages_repo import MessagesRepo
from app.repositories.sessions_repo import SessionsRepo
from app.core.db import get_engine

router = APIRouter()

def get_messages_repo() -> MessagesRepo:
    return MessagesRepo(get_engine())

def get_sessions_repo() -> SessionsRepo:
    return SessionsRepo(get_engine())

@router.get("/sessions/{session_id}/messages")
def history(
    session_id: str,
    messages_repo: MessagesRepo = Depends(get_messages_repo),
    sessions_repo: SessionsRepo = Depends(get_sessions_repo),
):
    session = sessions_repo.get_session(session_id)
    if not session or session.get("status") != "active":
        raise HTTPException(status_code=404, detail="session not found")

    messages = messages_repo.list_messages(session_id)
    title = session["title"]
    return {"session_id": session_id, "title": title, "messages": messages}
