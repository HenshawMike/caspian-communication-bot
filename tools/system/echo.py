"""System echo tool for argument validation and verification."""

from typing import Dict, Any
from pydantic import BaseModel, Field
from agent.tool_registry import register_tool
from agent.permissions import PermissionScope


class EchoInput(BaseModel):
    """Input parameters for echo tool."""
    message: str = Field(description="Message string to echo back", min_length=1)
    repeat_count: int = Field(default=1, ge=1, le=10, description="Number of times to repeat message")


class EchoOutput(BaseModel):
    """Output from echo tool."""
    echoed_message: str
    repetition: int


@register_tool(
    name="system_echo",
    description="Echo a message back to verify argument validation and execution flow.",
    permission=PermissionScope.SYSTEM_READ,
    args_model=EchoInput,
    output_model=EchoOutput,
)
def echo(message: str, repeat_count: int = 1) -> Dict[str, Any]:
    """Echo the input message with repetition."""
    return {
        "echoed_message": " ".join([message] * repeat_count),
        "repetition": repeat_count,
    }
