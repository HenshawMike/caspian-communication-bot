"""Tool to queue approved drafts into the scheduled publishing queue."""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from agent.tool_registry import register_tool
from agent.permissions import PermissionScope
from database.models import get_content_draft, db_manager


class QueuePostInput(BaseModel):
    """Input parameters for queue_post."""
    draft_id: str = Field(description="Unique ID of the approved draft to queue.")
    scheduled_time: Optional[str] = Field(default=None, description="ISO timestamp for scheduled release.")


class QueuePostOutput(BaseModel):
    """Output schema for queue_post."""
    success: bool
    draft_id: str
    scheduled_time: Optional[str] = None
    message: str
    error: Optional[str] = None


@register_tool(
    name="queue_post",
    description="Enqueue an approved and verified draft into the publishing schedule queue.",
    permission=PermissionScope.CONTENT_GENERATE,
    args_model=QueuePostInput,
    output_model=QueuePostOutput,
)
def queue_post(
    draft_id: str,
    scheduled_time: Optional[str] = None,
    manager: Optional[Any] = None,
) -> Dict[str, Any]:
    """Enqueue approved draft."""
    mgr = manager or db_manager
    draft = get_content_draft(draft_id, manager=mgr)
    if not draft:
        return {
            "success": False,
            "draft_id": draft_id,
            "scheduled_time": None,
            "message": f"Draft '{draft_id}' not found.",
            "error": "DRAFT_NOT_FOUND",
        }

    if draft["approval_status"] != "APPROVED":
        return {
            "success": False,
            "draft_id": draft_id,
            "scheduled_time": None,
            "message": f"Draft '{draft_id}' must be approved before queueing (status: {draft['approval_status']}).",
            "error": "NOT_APPROVED",
        }

    query = """
    UPDATE content_drafts
    SET publication_status = 'QUEUED', scheduled_time = ?, updated_at = CURRENT_TIMESTAMP
    WHERE draft_id = ?;
    """
    with mgr.connection() as conn:
        conn.execute(query, (scheduled_time, draft_id))

    return {
        "success": True,
        "draft_id": draft_id,
        "scheduled_time": scheduled_time,
        "message": f"Draft '{draft_id}' queued for scheduled publishing.",
        "error": None,
    }
