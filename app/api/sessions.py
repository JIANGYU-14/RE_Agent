from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.repositories.messages_repo import MessagesRepo
from app.repositories.sessions_repo import SessionsRepo
from app.core.db import get_engine


router = APIRouter()


# ---------- dependencies ----------

def get_sessions_repo() -> SessionsRepo:
    return SessionsRepo(get_engine())

def get_messages_repo() -> MessagesRepo:
    return MessagesRepo(get_engine())


# ---------- api ----------

class CreateSessionRequest(BaseModel):
    user_id: str


class RenameSessionRequest(BaseModel):
    title: str


@router.post("/sessions")
def create_session(
    payload: CreateSessionRequest,
    sessions_repo: SessionsRepo = Depends(get_sessions_repo),
):
    """
    创建一个新会话
    """
    return sessions_repo.create_session(payload.user_id)


@router.get("/sessions/list")
def list_user_sessions(
    user_id: str,
    sessions_repo: SessionsRepo = Depends(get_sessions_repo),
):
    """
    获取当前用户的所有会话（按 updated_at 倒序）
    """
    sessions = sessions_repo.list_sessions(user_id)
    return {"sessions": sessions}


@router.patch("/sessions/{session_id}/title")
def rename_session(
    session_id: str,
    payload: RenameSessionRequest,
    sessions_repo: SessionsRepo = Depends(get_sessions_repo),
):
    session = sessions_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")

    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="title is required")

    sessions_repo.update_title(session_id, title)
    return sessions_repo.get_session(session_id)


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: str,
    hard: bool = False,
    messages_repo: MessagesRepo = Depends(get_messages_repo),
    sessions_repo: SessionsRepo = Depends(get_sessions_repo),
):
    session = sessions_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")

    if hard:
        messages_repo.delete_by_session_id(session_id)
        sessions_repo.delete_session(session_id)
    else:
        sessions_repo.archive_session(session_id)
    return {"ok": True}
