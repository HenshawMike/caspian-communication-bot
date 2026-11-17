"""Knowledge context retrieval tool."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from agent.tool_registry import register_tool
from agent.permissions import PermissionScope
from database.models import retrieve_caspian_context


class RetrieveContextInput(BaseModel):
    """Input parameters for retrieve_context."""
    query: Optional[str] = Field(default=None, description="Keywords or topic to search prior research for.")
    disclosure_filter: Optional[str] = Field(default=None, description="Optional disclosure status filter (e.g. PUBLIC).")
    limit: int = Field(default=5, ge=1, le=20, description="Maximum number of historical records to retrieve.")


class StoredContextItem(BaseModel):
    """A single historical research context item."""
    id: int
    title: str
    experiment_id: Optional[str] = None
    commit_hash: Optional[str] = None
    findings: Optional[str] = None
    limitations: Optional[str] = None
    disclosure_status: str
    created_at: str


class RetrieveContextOutput(BaseModel):
    """Output schema for retrieve_context."""
    success: bool
    count: int
    items: List[StoredContextItem] = Field(default_factory=list)


@register_tool(
    name="retrieve_context",
    description="Retrieve prior Project Caspian research records, hypotheses, and experimental context from knowledge store.",
    permission=PermissionScope.KNOWLEDGE_READ,
    args_model=RetrieveContextInput,
    output_model=RetrieveContextOutput,
)
def retrieve_context(
    query: Optional[str] = None,
    disclosure_filter: Optional[str] = None,
    limit: int = 5,
) -> Dict[str, Any]:
    """Retrieve historical research context from database."""
    try:
        records = retrieve_caspian_context(
            query_text=query,
            disclosure_filter=disclosure_filter,
            limit=limit,
        )
        return {
            "success": True,
            "count": len(records),
            "items": records,
        }
    except Exception as e:
        return {
            "success": False,
            "count": 0,
            "items": [],
        }
