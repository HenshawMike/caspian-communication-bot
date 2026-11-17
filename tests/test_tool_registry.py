"""Tests for tool registry and declarations."""

import pytest
from pydantic import BaseModel, Field
from agent.tool_registry import ToolRegistry


class DummyInput(BaseModel):
    query: str = Field(description="Search query string")
    max_results: int = Field(default=5, ge=1)


class DummyOutput(BaseModel):
    results: list


def test_tool_registration():
    reg = ToolRegistry()

    @reg.register(
        name="dummy_search",
        description="Searches dummy data.",
        permission="knowledge_read",
        args_model=DummyInput,
        output_model=DummyOutput,
    )
    def dummy_func(query: str, max_results: int = 5):
        return {"results": [query] * max_results}

    assert reg.has_tool("dummy_search")
    tool = reg.get_tool("dummy_search")
    assert tool["name"] == "dummy_search"
    assert tool["permission"] == "knowledge_read"


def test_tool_duplicate_registration_fails():
    reg = ToolRegistry()

    @reg.register(name="unique_tool", description="A", permission="system_read")
    def tool_one():
        return {}

    with pytest.raises(ValueError) as exc:
        @reg.register(name="unique_tool", description="B", permission="system_read")
        def tool_two():
            return {}

    assert "already registered" in str(exc.value)


def test_gemini_declarations_export():
    reg = ToolRegistry()

    @reg.register(
        name="test_tool",
        description="A test tool",
        permission="system_read",
        args_model=DummyInput,
    )
    def test_tool(query: str, max_results: int = 5):
        return {}

    declarations = reg.to_gemini_declarations()
    assert len(declarations) == 1
    decl = declarations[0]
    assert decl["name"] == "test_tool"
    assert decl["description"] == "A test tool"
    assert "parameters" in decl
    assert "properties" in decl["parameters"]
    assert "query" in decl["parameters"]["properties"]
