"""Tool to inspect past publications and prevent duplicate attempts."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from agent.tool_registry import register_tool
from agent.permissions import PermissionScope
from database.models import get_publication_history as db_get_pub_history


class PublicationHistoryInput(BaseModel):
    """Input parameters for publication_history."""
    limit: int = Field(default=20, ge=1, le=100, description="Max history records to return.")


class PublicationHistoryOutput(BaseModel):
    """Output schema for publication_history."""
    success: bool
    count: int
    records: List[Dict[str, Any]] = Field(default_factory=list)


@register_tool(
    name="publication_history",
    description="Retrieve past publication records, timestamps, and status for audit and duplicate prevention.",
    permission=PermissionScope.KNOWLEDGE_READ,
    args_model=PublicationHistoryInput,
    output_model=PublicationHistoryOutput,
)
def publication_history(
    limit: int = 20,
    manager: Optional[Any] = None,
) -> Dict[str, Any]:
    """Retrieve publication logs."""
    records = db_get_pub_history(limit=limit, manager=manager)
    return {
        "success": True,
        "count": len(records),
        "records": records,
    }
