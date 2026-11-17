"""Schedule execution engine executing scheduled publishing of approved drafts."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from agent.tool_registry import register_tool
from agent.permissions import PermissionScope
from agent.logging_config import logger
from database.models import (
    get_publishing_schedule,
    get_pending_approved_drafts,
)
from tools.publishing.publish_x import publish_x


class ExecuteScheduleInput(BaseModel):
    """Input parameters for execute_schedule."""
    schedule_name: str = Field(default="default", description="Name of the schedule to trigger.")
    max_items: int = Field(default=1, ge=1, le=5, description="Max approved drafts to publish in this run.")


class PublishedItemSummary(BaseModel):
    """Summary of a published draft."""
    draft_id: str
    success: bool
    x_post_id: Optional[str] = None
    message: str


class ExecuteScheduleOutput(BaseModel):
    """Output schema for execute_schedule."""
    success: bool
    schedule_name: str
    is_paused: bool
    published_count: int
    published_items: List[PublishedItemSummary] = Field(default_factory=list)
    message: str
    error: Optional[str] = None


@register_tool(
    name="execute_schedule",
    description="Trigger a scheduled publishing tick. Publishes verified, approved queued drafts if schedule is active.",
    permission=PermissionScope.CONTENT_PUBLISH,
    args_model=ExecuteScheduleInput,
    output_model=ExecuteScheduleOutput,
)
def execute_schedule(
    schedule_name: str = "default",
    max_items: int = 1,
    manager: Optional[Any] = None,
) -> Dict[str, Any]:
    """Execute scheduled publishing run."""
    # 1. Verify schedule status
    sched = get_publishing_schedule(schedule_name=schedule_name, manager=manager)
    if not sched:
        return {
            "success": False,
            "schedule_name": schedule_name,
            "is_paused": False,
            "published_count": 0,
            "published_items": [],
            "message": f"Schedule '{schedule_name}' not found.",
            "error": "SCHEDULE_NOT_FOUND",
        }

    # CRITICAL RULE: Never publish when schedule is paused
    if sched["is_paused"]:
        logger.info(f"Schedule '{schedule_name}' is paused. Skipping scheduled publishing tick.")
        return {
            "success": True,
            "schedule_name": schedule_name,
            "is_paused": True,
            "published_count": 0,
            "published_items": [],
            "message": f"Schedule '{schedule_name}' is currently paused. No posts were published.",
            "error": None,
        }

    # 2. Retrieve pending approved drafts
    pending_drafts = get_pending_approved_drafts(limit=max_items, manager=manager)
    if not pending_drafts:
        return {
            "success": True,
            "schedule_name": schedule_name,
            "is_paused": False,
            "published_count": 0,
            "published_items": [],
            "message": "No approved and queued drafts are awaiting publication.",
            "error": None,
        }

    # 3. Publish approved drafts
    published_items = []
    for draft in pending_drafts:
        pub_res = publish_x(draft_id=draft["draft_id"], manager=manager)
        published_items.append(PublishedItemSummary(
            draft_id=draft["draft_id"],
            success=pub_res["success"],
            x_post_id=pub_res.get("x_post_id"),
            message=pub_res["message"],
        ).model_dump())

    success_count = sum(1 for p in published_items if p["success"])
    return {
        "success": True,
        "schedule_name": schedule_name,
        "is_paused": False,
        "published_count": success_count,
        "published_items": published_items,
        "message": f"Schedule executed: published {success_count} approved draft(s).",
        "error": None,
    }
