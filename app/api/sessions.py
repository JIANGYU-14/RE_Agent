from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.repositories.sessions_repo import SessionsRepo
from app.core.db import get_engine


router = APIRouter()


# ---------- dependencies ----------

def get_sessions_repo() -> SessionsRepo:
    return SessionsRepo(get_engine())


# ---------- api ----------

class CreateSessionRequest(BaseModel):
    user_id: str


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
