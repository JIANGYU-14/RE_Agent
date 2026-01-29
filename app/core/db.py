from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.config import settings
from app.repositories.messages_repo import metadata as messages_metadata
from app.repositories.sessions_repo import metadata as sessions_metadata


_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine

    if _engine is None:
        if not settings.database_url:
            raise RuntimeError(
                "DATABASE_URL 未配置：请在启动前设置环境变量 DATABASE_URL，例如 sqlite:///./dev.db 或 postgresql://user:pass@host:5432/db"
            )

        # FaaS 环境建议：连接池要小 + 必须加连接超时，避免启动阶段卡住导致 120s 超时重启
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=1,
            max_overflow=0,
            pool_recycle=300,
            connect_args={"connect_timeout": 5},  # psycopg2: seconds
        )

    return _engine


def init_db() -> None:
    """
    初始化表结构（DDL）。
    注意：不要在 FaaS 的 startup 阶段强制调用，否则网络不通会阻塞并导致平台启动超时重启。
    """
    engine = get_engine()
    messages_metadata.create_all(engine)
    sessions_metadata.create_all(engine)
