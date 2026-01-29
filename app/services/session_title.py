import logging
import os
import threading

from app.repositories.messages_repo import MessagesRepo
from app.repositories.sessions_repo import SessionsRepo
from app.core.db import get_engine
from app.core.title_agent_client import TitleAgentClient

logger = logging.getLogger(__name__)

title_agent = TitleAgentClient()


def _generate(session_id: str):
    engine = get_engine()
    messages_repo = MessagesRepo(engine)
    sessions_repo = SessionsRepo(engine)

    session = sessions_repo.get_session(session_id)
    if not session:
        logger.warning("skip title generation: session not found", extra={"session_id": session_id})
        return

    if session.get("title") and session.get("title") != "新对话":
        logger.info("skip title generation: title already set", extra={"session_id": session_id, "title": session.get("title")})
        return

    msgs = messages_repo.list_messages(session_id)
    if len(msgs) < 2:
        logger.warning(
            "skip title generation: not enough messages",
            extra={"session_id": session_id, "count": len(msgs)},
        )
        return

    # Extract text content from parts
    def get_content(m):
        if not m.get("parts"):
            return ""
        # Find first text part
        for p in m["parts"]:
            if p.get("type") == "text":
                return p.get("content") or ""
        return ""

    convo = "\n".join(
        f"{m['role']}: {get_content(m)}" for m in msgs[:4]
    )

    try:
        title = title_agent.generate(convo)
    except Exception:
        logger.exception("title generation failed", extra={"session_id": session_id})
        return

    if not title or not title.strip():
        logger.warning(
            "title generation returned empty",
            extra={"session_id": session_id},
        )
        return

    try:
        sessions_repo.update_title(session_id, title)
    except Exception:
        logger.exception(
            "title update failed",
            extra={"session_id": session_id, "title": title},
        )
        return

    logger.info("title updated", extra={"session_id": session_id, "title": title})


def async_generate(session_id: str):
    sync = os.getenv("TITLE_GENERATION_SYNC", "").strip().lower() in {"1", "true", "yes"}
    if sync:
        _generate(session_id)
        return

    threading.Thread(
        target=_generate,
        args=(session_id,),
        daemon=True
    ).start()
