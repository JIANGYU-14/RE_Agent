from __future__ import annotations

<<<<<<< HEAD
from datetime import datetime
=======
>>>>>>> bfb5c23 (Add session delete hard option and chat session validation)
from uuid import uuid4

from sqlalchemy import (
    Table,
    Column,
    String,
    Integer,
    DateTime,
    Text,
    MetaData,
    select,
    insert,
    update,
<<<<<<< HEAD
)
from sqlalchemy.engine import Engine

=======
    delete,
)
from sqlalchemy.engine import Engine

from app.core.time_utils import iso_bjt, now_bjt_naive

>>>>>>> bfb5c23 (Add session delete hard option and chat session validation)

metadata = MetaData()

sessions_table = Table(
    "sessions",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("session_id", String, nullable=False, unique=True),
    Column("user_id", String, nullable=False),
    Column("status", String, nullable=False),
    Column("title", Text, nullable=False),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
)


class SessionsRepo:
    def __init__(self, engine: Engine):
        self.engine = engine

    def create_session(self, user_id: str) -> dict:
<<<<<<< HEAD
        now = datetime.utcnow()
=======
        now = now_bjt_naive()
>>>>>>> bfb5c23 (Add session delete hard option and chat session validation)
        session_id = str(uuid4())

        stmt = insert(sessions_table).values(
            session_id=session_id,
            user_id=user_id,
            status="active",
            title="新对话",
            created_at=now,
            updated_at=now,
        )

        with self.engine.begin() as conn:
            conn.execute(stmt)

        return {
            "session_id": session_id,
            "user_id": user_id,
            "status": "active",
            "title": "新对话",
<<<<<<< HEAD
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
=======
            "created_at": iso_bjt(now),
            "updated_at": iso_bjt(now),
>>>>>>> bfb5c23 (Add session delete hard option and chat session validation)
        }

    def list_sessions(self, user_id: str) -> list[dict]:
        stmt = (
            select(
                sessions_table.c.session_id,
                sessions_table.c.user_id,
                sessions_table.c.status,
                sessions_table.c.title,
                sessions_table.c.created_at,
                sessions_table.c.updated_at,
            )
            .where(sessions_table.c.user_id == user_id)
            .where(sessions_table.c.status == "active")
            .order_by(sessions_table.c.updated_at.desc())
        )

        with self.engine.begin() as conn:
            rows = conn.execute(stmt).mappings().all()

        return [
            {
                "session_id": r["session_id"],
                "user_id": r["user_id"],
                "status": r["status"],
                "title": r["title"],
<<<<<<< HEAD
                "created_at": r["created_at"].isoformat(),
                "updated_at": r["updated_at"].isoformat(),
=======
                "created_at": iso_bjt(r["created_at"]),
                "updated_at": iso_bjt(r["updated_at"]),
>>>>>>> bfb5c23 (Add session delete hard option and chat session validation)
            }
            for r in rows
        ]

    def get_session(self, session_id: str) -> dict | None:
        stmt = (
            select(
                sessions_table.c.session_id,
                sessions_table.c.user_id,
                sessions_table.c.status,
                sessions_table.c.title,
                sessions_table.c.created_at,
                sessions_table.c.updated_at,
            )
            .where(sessions_table.c.session_id == session_id)
            .limit(1)
        )

        with self.engine.begin() as conn:
            row = conn.execute(stmt).mappings().first()

        if not row:
            return None

        return {
            "session_id": row["session_id"],
            "user_id": row["user_id"],
            "status": row["status"],
            "title": row["title"],
<<<<<<< HEAD
            "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat(),
=======
            "created_at": iso_bjt(row["created_at"]),
            "updated_at": iso_bjt(row["updated_at"]),
>>>>>>> bfb5c23 (Add session delete hard option and chat session validation)
        }

    def touch_session(self, session_id: str) -> None:
        stmt = (
            update(sessions_table)
            .where(sessions_table.c.session_id == session_id)
<<<<<<< HEAD
            .values(updated_at=datetime.utcnow())
=======
            .values(updated_at=now_bjt_naive())
>>>>>>> bfb5c23 (Add session delete hard option and chat session validation)
        )

        with self.engine.begin() as conn:
            conn.execute(stmt)

    def update_title(self, session_id: str, title: str) -> None:
        stmt = (
            update(sessions_table)
            .where(sessions_table.c.session_id == session_id)
            .values(
                title=title,
<<<<<<< HEAD
                updated_at=datetime.utcnow(),
=======
                updated_at=now_bjt_naive(),
>>>>>>> bfb5c23 (Add session delete hard option and chat session validation)
            )
        )

        with self.engine.begin() as conn:
            conn.execute(stmt)

    def archive_session(self, session_id: str) -> None:
        stmt = (
            update(sessions_table)
            .where(sessions_table.c.session_id == session_id)
            .values(
                status="archived",
<<<<<<< HEAD
                updated_at=datetime.utcnow(),
=======
                updated_at=now_bjt_naive(),
>>>>>>> bfb5c23 (Add session delete hard option and chat session validation)
            )
        )

        with self.engine.begin() as conn:
            conn.execute(stmt)
<<<<<<< HEAD
=======

    def delete_session(self, session_id: str) -> None:
        stmt = delete(sessions_table).where(sessions_table.c.session_id == session_id)

        with self.engine.begin() as conn:
            conn.execute(stmt)
>>>>>>> bfb5c23 (Add session delete hard option and chat session validation)
