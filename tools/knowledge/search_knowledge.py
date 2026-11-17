"""Knowledge search tool querying persistent AI intelligence records."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from agent.tool_registry import register_tool
from agent.permissions import PermissionScope
from database.models import search_external_knowledge


class SearchKnowledgeInput(BaseModel):
    """Input parameters for search_knowledge."""
    query: Optional[str] = Field(default=None, description="Keywords to match in title, summary, or contribution.")
    topic: Optional[str] = Field(default=None, description="Domain topic filter (e.g. 'world_models', 'reasoning_agents').")
    research_type: Optional[str] = Field(default=None, description="Optional type filter (e.g. 'preprint', 'announcement').")
    limit: int = Field(default=5, ge=1, le=20, description="Maximum number of records to return.")


class StoredKnowledgeRecord(BaseModel):
    """A matched research record."""
    id: int
    title: str
    source_url: str
    source_name: str
    publication_date: Optional[str] = None
    research_type: str
    topic: str
    summary: Optional[str] = None
    central_contribution: Optional[str] = None
    relevance_score: float
    importance_score: float
    created_at: str


class SearchKnowledgeOutput(BaseModel):
    """Output schema for search_knowledge."""
    success: bool
    count: int
    results: List[StoredKnowledgeRecord] = Field(default_factory=list)


@register_tool(
    name="search_knowledge",
    description="Search persistent external AI intelligence store by keywords, topic, or publication type.",
    permission=PermissionScope.KNOWLEDGE_READ,
    args_model=SearchKnowledgeInput,
    output_model=SearchKnowledgeOutput,
)
def search_knowledge(
    query: Optional[str] = None,
    topic: Optional[str] = None,
    research_type: Optional[str] = None,
    limit: int = 5,
    manager: Optional[Any] = None,
) -> Dict[str, Any]:
    """Execute search on external AI intelligence."""
    try:
        records = search_external_knowledge(
            query_text=query,
            topic=topic,
            research_type=research_type,
            limit=limit,
            manager=manager,
        )
        return {
            "success": True,
            "count": len(records),
            "results": records,
        }
    except Exception as e:
        return {
            "success": False,
            "count": 0,
            "results": [],
        }
