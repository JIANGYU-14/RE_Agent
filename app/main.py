from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api import sessions, chat, history
from app.core.db import get_engine, init_db

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    # FaaS 冷启动必须轻量化：不要在这里做 DB 连接/建表
    pass


# ---- Health / Admin endpoints (推荐保留，用于上线后快速验证网络与DB权限) ----

@app.get("/health/db")
def health_db():
    """
    验证：函数是否已正确绑定 VPC、PostgreSQL 安全组是否放行、连接串是否正确。
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("select 1"))
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"db not ready: {e}")


@app.post("/admin/init-db")
def admin_init_db():
    """
    仅用于首次部署初始化建表。生产建议加鉴权（例如内部 Header Token）或仅内网可达。
    """
    try:
        init_db()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"init_db failed: {e}")


# ---- Routers ----
app.include_router(sessions.router, prefix="/paperapi")
app.include_router(chat.router, prefix="/paperapi")
app.include_router(history.router, prefix="/paperapi")
