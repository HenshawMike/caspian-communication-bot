"""Tests for system tools ping and echo."""

from agent.tool_executor import executor
from agent.permissions import create_default_context
from tools.system import ping, echo


def test_system_ping_execution():
    ctx = create_default_context(user_id="test_user")
    res = executor.execute("system_ping", {}, context=ctx)
    assert res.success is True
    assert res.data["status"] == "healthy"
    assert "timestamp" in res.data


def test_system_echo_execution():
    ctx = create_default_context(user_id="test_user")
    res = executor.execute("system_echo", {"message": "hello", "repeat_count": 3}, context=ctx)
    assert res.success is True
    assert res.data["echoed_message"] == "hello hello hello"
    assert res.data["repetition"] == 3


def test_system_echo_validation_failure():
    ctx = create_default_context(user_id="test_user")
    # Empty message violates min_length=1
    res = executor.execute("system_echo", {"message": ""}, context=ctx)
    assert res.success is False
    assert res.error.code == "INVALID_ARGUMENTS"
