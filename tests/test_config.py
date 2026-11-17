"""Tests for configuration management."""

import os
from pathlib import Path
from agent.config import Settings


def test_settings_defaults():
    s = Settings(gemini_api_key=None, telegram_bot_token=None)
    assert s.gemini_model == "gemini-2.5-flash"
    assert s.database_path == "caspian_agent.db"
    assert s.max_tool_calls_per_request == 10
    assert "Settings" in repr(s)


def test_settings_redaction_in_repr():
    s = Settings(
        gemini_api_key="AIzaSySecretApiKey1234567890",
        telegram_bot_token="123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
    )
    rep = repr(s)
    assert "AIzaSySecret" not in rep
    assert "ABCdefGHI" not in rep
    assert "***" in rep


def test_get_db_path(tmp_path):
    s = Settings(base_dir=tmp_path, database_path="test.db")
    assert s.get_db_path() == tmp_path / "test.db"
