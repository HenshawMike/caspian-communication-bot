"""Deduplication tool checking candidate items against stored knowledge."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from agent.tool_registry import register_tool
from agent.permissions import PermissionScope
from database.models import is_source_url_stored


class DeduplicateCandidate(BaseModel):
    """Candidate item to verify."""
    title: str
    url: str


class DeduplicateInput(BaseModel):
    """Input parameters for deduplicate."""
    candidates: List[Dict[str, Any]] = Field(description="List of candidate items with 'url' and 'title'.")


class DeduplicateOutput(BaseModel):
    """Output schema for deduplicate."""
    success: bool
    total_candidates: int
    new_count: int
    duplicate_count: int
    new_items: List[Dict[str, Any]] = Field(default_factory=list)
    duplicates: List[str] = Field(default_factory=list)


@register_tool(
    name="deduplicate",
    description="Filter candidate research sources against persistent knowledge store to prevent duplicate entries.",
    permission=PermissionScope.KNOWLEDGE_READ,
    args_model=DeduplicateInput,
    output_model=DeduplicateOutput,
)
def deduplicate(
    candidates: List[Dict[str, Any]],
    manager: Optional[Any] = None,
) -> Dict[str, Any]:
    """Remove already stored or duplicate records."""
    seen_urls = set()
    new_items = []
    duplicate_urls = []

    for item in candidates:
        raw_url = str(item.get("url") or item.get("source_url") or "").strip()
        if not raw_url:
            continue

        # In-batch deduplication
        if raw_url in seen_urls:
            duplicate_urls.append(raw_url)
            continue
        seen_urls.add(raw_url)

        # Database deduplication
        if is_source_url_stored(raw_url, manager=manager):
            duplicate_urls.append(raw_url)
        else:
            new_items.append(item)

    return {
        "success": True,
        "total_candidates": len(candidates),
        "new_count": len(new_items),
        "duplicate_count": len(duplicate_urls),
        "new_items": new_items,
        "duplicates": duplicate_urls,
    }
