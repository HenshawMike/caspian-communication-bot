"""System diagnostic ping tool."""

from typing import Dict, Any
from pydantic import BaseModel, Field
from agent.tool_registry import register_tool
from agent.permissions import PermissionScope


class PingOutput(BaseModel):
    """Output for system ping tool."""
    status: str = Field(description="Health status of the agent system")
    timestamp: str = Field(description="Timestamp of response")


@register_tool(
    name="system_ping",
    description="Check the operational status of the agent system.",
    permission=PermissionScope.SYSTEM_READ,
    output_model=PingOutput,
)
def ping() -> Dict[str, Any]:
    """Execute ping healthcheck."""
    from datetime import datetime, timezone
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
