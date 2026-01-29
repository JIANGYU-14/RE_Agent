import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, JSON
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# --- Monkeypatching SQLAlchemy JSONB for SQLite ---
# This allows using "postgresql" code with "sqlite" for testing
import sqlalchemy.dialects.postgresql
sqlalchemy.dialects.postgresql.JSONB = JSON

# Import app modules after patching
from app.main import app
from app.core import db
from app.repositories.messages_repo import metadata as messages_metadata
from app.repositories.sessions_repo import metadata as sessions_metadata

# Use in-memory SQLite database
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(name="session")
def session_fixture():
    # Create tables
    messages_metadata.create_all(bind=engine)
    sessions_metadata.create_all(bind=engine)
    
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()
    
    # Drop all tables to ensure clean state for next test
    messages_metadata.drop_all(bind=engine)
    sessions_metadata.drop_all(bind=engine)


@pytest.fixture(name="client")
def client_fixture(session):
    # Mock AgentKitClient to avoid external calls
    mock_agent = MagicMock()
    
    # Mock async generator for astream_chat
    async def mock_astream_chat(*args, **kwargs):
        yield {"type": "text", "content": "Mocked "}
        yield {"type": "text", "content": "Agent "}
        yield {"type": "text", "content": "Response"}

    mock_agent.astream_chat = mock_astream_chat
    
    # Inject our test engine into the db module's global variable
    original_engine = db._engine
    db._engine = engine
    
    # Patch the global 'agent' instance in api/chat.py
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("app.api.chat.agent", mock_agent)
        yield TestClient(app)
    
    # Restore original engine
    db._engine = original_engine
