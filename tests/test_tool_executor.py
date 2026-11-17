"""Tests for tool executor, validation, and permissions."""

from pydantic import BaseModel, Field
from agent.tool_registry import ToolRegistry
from agent.tool_executor import ToolExecutor
from agent.permissions import PermissionContext, PermissionScope


class SampleInput(BaseModel):
    name: str = Field(min_length=2)
    score: int = Field(ge=0, le=100)


def test_tool_executor_success(temp_db):
    reg = ToolRegistry()

    @reg.register(
        name="calculate_score",
        description="Calculates a score",
        permission=PermissionScope.SYSTEM_READ,
        args_model=SampleInput,
    )
    def calc(name: str, score: int):
        return {"result": f"{name}: {score * 2}"}

    executor = ToolExecutor(tool_registry=reg)
    ctx = PermissionContext(user_id="user_test")
    ctx.add_scope(PermissionScope.SYSTEM_READ)

    envelope = executor.execute("calculate_score", {"name": "Alice", "score": 40}, context=ctx)

    assert envelope.success is True
    assert envelope.data == {"result": "Alice: 80"}
    assert envelope.error is None
    assert envelope.execution_metadata.tool_name == "calculate_score"
    assert envelope.execution_metadata.duration_ms >= 0


def test_tool_executor_permission_denied():
    reg = ToolRegistry()

    @reg.register(
        name="restricted_tool",
        description="Restricted tool",
        permission=PermissionScope.CONTENT_PUBLISH,
    )
    def restricted():
        return {"status": "published"}

    executor = ToolExecutor(tool_registry=reg)
    ctx = PermissionContext(user_id="user_test")
    # Only SYSTEM_READ granted, not CONTENT_PUBLISH
    ctx.add_scope(PermissionScope.SYSTEM_READ)

    envelope = executor.execute("restricted_tool", {}, context=ctx)
    assert envelope.success is False
    assert envelope.error.code == "PERMISSION_DENIED"
    assert "Permission denied" in envelope.error.message


def test_tool_executor_invalid_arguments():
    reg = ToolRegistry()

    @reg.register(
        name="validate_args_tool",
        description="Tool with validation",
        permission=PermissionScope.SYSTEM_READ,
        args_model=SampleInput,
    )
    def valid_tool(name: str, score: int):
        return {}

    executor = ToolExecutor(tool_registry=reg)
    ctx = PermissionContext()
    ctx.add_scope(PermissionScope.SYSTEM_READ)

    # Score out of bounds (score=999 > 100)
    envelope = executor.execute("validate_args_tool", {"name": "Bob", "score": 999}, context=ctx)
    assert envelope.success is False
    assert envelope.error.code == "INVALID_ARGUMENTS"
    assert "validation_errors" in envelope.error.details


def test_tool_executor_unregistered_tool():
    reg = ToolRegistry()
    executor = ToolExecutor(tool_registry=reg)

    envelope = executor.execute("non_existent_tool", {})
    assert envelope.success is False
    assert envelope.error.code == "TOOL_NOT_FOUND"
