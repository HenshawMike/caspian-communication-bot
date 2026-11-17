"""Structured document creation tool separating content from styling."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from agent.tool_registry import register_tool
from agent.permissions import PermissionScope
from agent.logging_config import logger


class TableModel(BaseModel):
    """Structured table representation."""
    headers: List[str] = Field(default_factory=list, description="Column header labels.")
    rows: List[List[str]] = Field(default_factory=list, description="Matrix of row cell values.")


class SectionModel(BaseModel):
    """Structured document section."""
    heading: str = Field(description="Main heading for this section.")
    subheading: Optional[str] = Field(default=None, description="Optional secondary section heading.")
    paragraphs: List[str] = Field(default_factory=list, description="Body paragraphs.")
    bullet_points: List[str] = Field(default_factory=list, description="Key bullet points or findings.")
    callouts: List[str] = Field(default_factory=list, description="Callout notes or caveats.")
    table: Optional[TableModel] = Field(default=None, description="Optional structured table.")


class CreateDocumentInput(BaseModel):
    """Input parameters for create_document."""
    title: str = Field(description="Primary title of the document.")
    document_type: str = Field(
        default="research_summary",
        description="Type: research_summary, daily_briefing, research_report, content_plan, technical_doc.",
    )
    subtitle: Optional[str] = Field(default=None, description="Document subtitle or tagline.")
    sections: List[SectionModel] = Field(default_factory=list, description="Sequential document sections.")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Metadata dictionary (date, author, classification, experiment_id, etc.).",
    )
    sources: Optional[List[str]] = Field(default=None, description="List of original citations or URLs.")


class CreateDocumentOutput(BaseModel):
    """Output schema for create_document."""
    success: bool
    document_id: str
    document_type: str
    title: str
    section_count: int
    document_structure: Dict[str, Any]
    message: str


@register_tool(
    name="create_document",
    description="Constructs a validated, structured document model from validated research content, keeping content strictly separated from styling.",
    permission=PermissionScope.CONTENT_GENERATE,
    args_model=CreateDocumentInput,
    output_model=CreateDocumentOutput,
)
def create_document(
    title: str,
    document_type: str = "research_summary",
    subtitle: Optional[str] = None,
    sections: Optional[List[Dict[str, Any]]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    sources: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Create a structured document model."""
    doc_id = f"DOC-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
    created_at = datetime.now(timezone.utc).isoformat()

    valid_types = {
        "research_summary",
        "daily_briefing",
        "research_report",
        "content_plan",
        "technical_doc",
    }
    normalized_type = document_type.lower().strip()
    if normalized_type not in valid_types:
        normalized_type = "research_summary"

    doc_meta = metadata.copy() if metadata else {}
    doc_meta.setdefault("created_at", created_at)
    doc_meta.setdefault("document_id", doc_id)
    doc_meta.setdefault("classification", "PUBLIC")

    # Parse and validate sections
    parsed_sections = []
    raw_sections = sections or []
    for s in raw_sections:
        if isinstance(s, dict):
            parsed_sections.append(SectionModel(**s).model_dump())
        elif isinstance(s, SectionModel):
            parsed_sections.append(s.model_dump())

    document_structure = {
        "document_id": doc_id,
        "title": title.strip(),
        "subtitle": subtitle.strip() if subtitle else None,
        "document_type": normalized_type,
        "metadata": doc_meta,
        "sections": parsed_sections,
        "sources": sources or [],
    }

    logger.info(f"Created structured document '{doc_id}' with {len(parsed_sections)} sections.")

    return {
        "success": True,
        "document_id": doc_id,
        "document_type": normalized_type,
        "title": title.strip(),
        "section_count": len(parsed_sections),
        "document_structure": document_structure,
        "message": f"Document '{title}' ({doc_id}) structured successfully with {len(parsed_sections)} sections.",
    }
