"""Content extraction and prompt-injection sanitization for external sources."""

import re
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from agent.tool_registry import register_tool
from agent.permissions import PermissionScope
from agent.logging_config import logger


class ExtractContentInput(BaseModel):
    """Input parameters for extract_content."""
    raw_text: str = Field(description="Raw text, abstract, or paper body retrieved from external source.")
    source_url: str = Field(description="Original URL of the external publication.")
    title: Optional[str] = Field(default=None, description="Title of the publication.")


class ExtractedResearchContent(BaseModel):
    """Sanitized and structured research content."""
    title: str
    source_url: str
    cleaned_text: str
    abstract: str
    methods_overview: Optional[str] = None
    key_findings: Optional[str] = None
    word_count: int


class ExtractContentOutput(BaseModel):
    """Output schema for extract_content."""
    success: bool
    data: ExtractedResearchContent


def _sanitize_untrusted_content(text: str) -> str:
    """Neutralize potential prompt injection attempts in untrusted web text."""
    # Strip HTML tags
    clean = re.sub(r"<[^>]+>", " ", text)
    # Neutralize injection patterns by wrapping in quotes or disarming
    disarm_patterns = [
        re.compile(r"\b(ignore\s+(all\s+)?(previous|prior)\s+instructions?)\b", re.IGNORECASE),
        re.compile(r"\b(system\s+prompt\s*:)\b", re.IGNORECASE),
        re.compile(r"\b(you\s+are\s+now\s+a\b)", re.IGNORECASE),
    ]
    for p in disarm_patterns:
        clean = p.sub(r"[DISARMED_INSTRUCTION: \1]", clean)
    return re.sub(r"\s+", " ", clean).strip()


@register_tool(
    name="extract_content",
    description="Clean, structure, and sanitize untrusted external research text, neutralizing injection risks.",
    permission=PermissionScope.EXTERNAL_READ,
    args_model=ExtractContentInput,
    output_model=ExtractContentOutput,
)
def extract_content(
    raw_text: str,
    source_url: str,
    title: Optional[str] = None,
) -> Dict[str, Any]:
    """Sanitize and structure external research text."""
    sanitized = _sanitize_untrusted_content(raw_text)
    doc_title = title or "External AI Publication"

    # Separate abstract from body if present
    abstract = sanitized[:600].strip()
    findings = None
    methods = None

    findings_match = re.search(r"(?:results?|findings?|conclusion)[:\s]+([^.]+)", sanitized, re.IGNORECASE)
    if findings_match:
        findings = findings_match.group(1).strip()

    methods_match = re.search(r"(?:methodology|methods?|approach)[:\s]+([^.]+)", sanitized, re.IGNORECASE)
    if methods_match:
        methods = methods_match.group(1).strip()

    word_count = len(sanitized.split())

    content_obj = ExtractedResearchContent(
        title=doc_title,
        source_url=source_url,
        cleaned_text=sanitized,
        abstract=abstract,
        methods_overview=methods,
        key_findings=findings,
        word_count=word_count,
    )

    return {
        "success": True,
        "data": content_obj.model_dump(),
    }
