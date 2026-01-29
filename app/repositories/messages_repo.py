from __future__ import annotations

from datetime import datetime
from typing import List, Dict, Any

from sqlalchemy import (
    Table,
    Column,
    String,
    Integer,
    DateTime,
    Text,
    MetaData,
    ForeignKey,
    select,
    insert,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine


metadata = MetaData()

# ---------- tables ----------

messages_table = Table(
    "messages",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("session_id", String, nullable=False),
    Column("role", String(16), nullable=False),
    Column("created_at", DateTime, nullable=False),
)

message_parts_table = Table(
    "message_parts",
    metadata,
    Column("id", Integer, primary_key=True),
    Column(
        "message_id",
        Integer,
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("type", String(16), nullable=False),  # text / image / audio / tool
    Column("content", Text),
    Column("url", Text),
    Column("metadata", JSONB),
    Column("sort_order", Integer, nullable=False),
)


# ---------- repository ----------

class MessagesRepo:
    def __init__(self, engine: Engine):
        self.engine = engine

    # ========== 写入 ==========

    def save_message(
        self,
        session_id: str,
        role: str,
        parts: List[Dict[str, Any]],
    ) -> None:
        """
        parts example:
        [
            {"type": "text", "content": "你好"},
            {"type": "image", "url": "https://xxx/a.png"}
        ]
        """

        now = datetime.utcnow()

        with self.engine.begin() as conn:
            # 1️⃣ insert message (INT4 id)
            result = conn.execute(
                insert(messages_table)
                .values(
                    session_id=session_id,
                    role=role,
                    created_at=now,
                )
                .returning(messages_table.c.id)
            )

            message_id: int = result.scalar_one()

            # 2️⃣ insert message parts (INT4 message_id)
            for idx, part in enumerate(parts):
                conn.execute(
                    insert(message_parts_table).values(
                        message_id=message_id,
                        type=part["type"],
                        content=part.get("content"),
                        url=part.get("url"),
                        metadata=part.get("metadata"),
                        sort_order=idx,
                    )
                )

    # ========== 读取 ==========

    def list_messages(self, session_id: str) -> List[Dict[str, Any]]:
        stmt = (
            select(
                messages_table.c.id.label("message_id"),
                messages_table.c.role,
                messages_table.c.created_at,
                message_parts_table.c.type,
                message_parts_table.c.content,
                message_parts_table.c.url,
                message_parts_table.c.metadata,
                message_parts_table.c.sort_order,
            )
            .join(
                message_parts_table,
                messages_table.c.id == message_parts_table.c.message_id,
                isouter=True,
            )
            .where(messages_table.c.session_id == session_id)
            .order_by(
                messages_table.c.created_at.asc(),
                message_parts_table.c.sort_order.asc(),
            )
        )

        with self.engine.begin() as conn:
            rows = conn.execute(stmt).mappings().all()

        messages: Dict[int, Dict[str, Any]] = {}

        for r in rows:
            mid: int = r["message_id"]

            if mid not in messages:
                messages[mid] = {
                    "role": r["role"],
                    "created_at": r["created_at"].isoformat(),
                    "parts": [],
                }

            if r["type"] is not None:
                messages[mid]["parts"].append(
                    {
                        "type": r["type"],
                        "content": r["content"],
                        "url": r["url"],
                        "metadata": r["metadata"],
                    }
                )

        return list(messages.values())
