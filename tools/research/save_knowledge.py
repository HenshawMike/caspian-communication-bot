"""Persistent knowledge storage tool for external AI intelligence."""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from agent.tool_registry import register_tool
from agent.permissions import PermissionScope
from database.models import save_external_knowledge


class SaveKnowledgeInput(BaseModel):
    """Input parameters for save_knowledge."""
    title: str = Field(description="Title of research paper or announcement.")
    source_url: str = Field(description="Original permanent URL.")
    source_name: str = Field(default="External", description="Name of source, e.g. arXiv, DeepMind.")
    publication_date: Optional[str] = Field(default=None, description="Original publication ISO date.")
    research_type: str = Field(default="preprint", description="preprint, paper, announcement, opinion.")
    topic: str = Field(default="general_ai", description="Domain topic, e.g. world_models, reasoning_agents.")
    summary: Optional[str] = Field(default=None, description="Brief summary.")
    central_contribution: Optional[str] = Field(default=None, description="Core novelty or claim.")
    findings: Optional[str] = Field(default=None, description="Empirical or experimental findings.")
    relevance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    importance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    raw_content: Optional[str] = Field(default=None, description="Cleaned readable source text.")


class SaveKnowledgeOutput(BaseModel):
    """Output schema for save_knowledge."""
    success: bool
    record_id: int
    title: str
    source_url: str
    message: str


@register_tool(
    name="save_knowledge",
    description="Save a structured external AI intelligence record to persistent database storage.",
    permission=PermissionScope.KNOWLEDGE_WRITE,
    args_model=SaveKnowledgeInput,
    output_model=SaveKnowledgeOutput,
)
def save_knowledge(
    title: str,
    source_url: str,
    source_name: str = "External",
    publication_date: Optional[str] = None,
    research_type: str = "preprint",
    topic: str = "general_ai",
    summary: Optional[str] = None,
    central_contribution: Optional[str] = None,
    findings: Optional[str] = None,
    relevance_score: float = 0.5,
    importance_score: float = 0.5,
    raw_content: Optional[str] = None,
    manager: Optional[Any] = None,
) -> Dict[str, Any]:
    """Store external research record in SQLite."""
    try:
        rec_id = save_external_knowledge(
            title=title,
            source_url=source_url,
            source_name=source_name,
            publication_date=publication_date,
            research_type=research_type,
            topic=topic,
            summary=summary,
            central_contribution=central_contribution,
            findings=findings,
            relevance_score=relevance_score,
            importance_score=importance_score,
            raw_content=raw_content,
            manager=manager,
        )
        return {
            "success": True,
            "record_id": rec_id,
            "title": title,
            "source_url": source_url,
            "message": f"Successfully stored '{title}' with ID {rec_id}.",
        }
    except Exception as e:
        return {
            "success": False,
            "record_id": -1,
            "title": title,
            "source_url": source_url,
            "message": f"Storage error: {str(e)}",
        }
