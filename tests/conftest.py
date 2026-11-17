"""Pytest fixtures and configuration for testing."""

import os
import tempfile
import pytest
from pathlib import Path
from agent.config import Settings
from database.connection import DatabaseManager
from database.models import initialize_database
from agent.permissions import PermissionContext, PermissionScope
from agent.llm import MockLLMClient


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database for test isolation."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    mgr = DatabaseManager(db_path=db_path)
    initialize_database(mgr)
    yield mgr

    # Cleanup
    try:
        if db_path.exists():
            db_path.unlink()
        wal = db_path.with_name(db_path.name + "-wal")
        shm = db_path.with_name(db_path.name + "-shm")
        if wal.exists():
            wal.unlink()
        if shm.exists():
            shm.unlink()
    except Exception:
        pass


@pytest.fixture
def test_permissions():
    """Fixture providing a standard test permission context."""
    ctx = PermissionContext(user_id="test_user_1", active_skill="test_skill")
    ctx.add_scope(PermissionScope.SYSTEM_READ)
    ctx.add_scope(PermissionScope.REPOSITORY_READ)
    ctx.add_scope(PermissionScope.KNOWLEDGE_READ)
    return ctx


@pytest.fixture
def mock_llm():
    """Fixture providing a mock LLM client."""
    return MockLLMClient()
