"""Multi-post thread generation tool adhering to X character constraints."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from agent.tool_registry import register_tool
from agent.permissions import PermissionScope
from agent.logging_config import logger


class GenerateThreadInput(BaseModel):
    """Input parameters for generate_thread."""
    topic: str = Field(description="Core research subject or breakthrough.")
    key_points: List[str] = Field(description="Sequential points or findings to format into a thread.")
    source_reference: Optional[str] = Field(default=None, description="Paper URL, experiment ID, or commit hash.")


class ThreadPost(BaseModel):
    """A single tweet in a thread."""
    index: int
    text: str
    char_count: int


class GenerateThreadOutput(BaseModel):
    """Output schema for generate_thread."""
    success: bool
    total_posts: int
    posts: List[ThreadPost] = Field(default_factory=list)
    topic: str
    source_reference: Optional[str] = None


@register_tool(
    name="generate_thread",
    description="Generate a cohesive, multi-part X thread (max 280 characters per tweet) with numbering and citations.",
    permission=PermissionScope.CONTENT_GENERATE,
    args_model=GenerateThreadInput,
    output_model=GenerateThreadOutput,
)
def generate_thread(
    topic: str,
    key_points: List[str],
    source_reference: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate structured multi-part thread."""
    if not key_points:
        return {
            "success": False,
            "total_posts": 0,
            "posts": [],
            "topic": topic,
            "source_reference": source_reference,
        }

    posts: List[ThreadPost] = []
    total_count = len(key_points)

    for i, point in enumerate(key_points, 1):
        prefix = f"{i}/{total_count} "
        suffix = f"\n\nSource: {source_reference}" if (i == total_count and source_reference) else ""
        
        # Calculate available room
        available = 280 - len(prefix) - len(suffix)
        body = point.strip()
        if len(body) > available:
            body = body[:available - 3].rstrip() + "..."

        tweet_text = prefix + body + suffix
        posts.append(ThreadPost(
            index=i,
            text=tweet_text,
            char_count=len(tweet_text),
        ))

    return {
        "success": True,
        "total_posts": len(posts),
        "posts": [p.model_dump() for p in posts],
        "topic": topic,
        "source_reference": source_reference,
    }
