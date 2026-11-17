"""Draft post generation tool adhering to research communication rules."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from agent.tool_registry import register_tool
from agent.permissions import PermissionScope
from agent.logging_config import logger


class GeneratePostInput(BaseModel):
    """Input parameters for generate_post."""
    topic: str = Field(description="Core research topic or milestone.")
    findings: str = Field(description="Verified public research findings.")
    limitations: Optional[str] = Field(default=None, description="Known limitations or caveats.")
    source_reference: Optional[str] = Field(default=None, description="Experiment ID, commit hash, or URL reference.")


class GeneratePostOutput(BaseModel):
    """Output schema for generate_post."""
    success: bool
    post_text: str
    character_count: int
    topic: str
    source_reference: Optional[str] = None


@register_tool(
    name="generate_post",
    description="Generate a balanced, concise research post draft from verified public findings (max 280 chars).",
    permission=PermissionScope.CONTENT_GENERATE,
    args_model=GeneratePostInput,
    output_model=GeneratePostOutput,
)
def generate_post(
    topic: str,
    findings: str,
    limitations: Optional[str] = None,
    source_reference: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a clean, professional research post."""
    # Compose draft
    ref_suffix = f" [{source_reference}]" if source_reference else ""
    core_text = f"Project Caspian Update: {topic.strip()}\n\n{findings.strip()}"
    
    if limitations:
        caveat = f"\n\nNote: {limitations.strip()}"
        if len(core_text) + len(caveat) + len(ref_suffix) <= 280:
            core_text += caveat

    if len(core_text) + len(ref_suffix) <= 280:
        draft = core_text + ref_suffix
    else:
        # Truncate cleanly if needed
        allowed_len = 280 - len(ref_suffix) - 3
        draft = core_text[:allowed_len].rstrip() + "..." + ref_suffix

    return {
        "success": True,
        "post_text": draft,
        "character_count": len(draft),
        "topic": topic,
        "source_reference": source_reference,
    }
