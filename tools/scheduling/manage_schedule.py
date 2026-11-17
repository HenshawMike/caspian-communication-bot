"""Tool to manage, pause, resume, and inspect publishing schedules."""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from agent.tool_registry import register_tool
from agent.permissions import PermissionScope
from database.models import get_publishing_schedule, set_schedule_paused


class ManageScheduleInput(BaseModel):
    """Input parameters for manage_schedule."""
    schedule_name: str = Field(default="default", description="Name of the schedule to manage.")
    action: str = Field(
        default="status",
        description="Action to perform: 'pause', 'resume', or 'status'.",
    )


class ManageScheduleOutput(BaseModel):
    """Output schema for manage_schedule."""
    success: bool
    schedule_name: str
    action: str
    is_paused: bool
    cadence: Optional[str] = None
    message: str
    error: Optional[str] = None


@register_tool(
    name="manage_schedule",
    description="Pause, resume, or check the status of the publishing schedule.",
    permission=PermissionScope.SYSTEM_READ,
    args_model=ManageScheduleInput,
    output_model=ManageScheduleOutput,
)
def manage_schedule(
    schedule_name: str = "default",
    action: str = "status",
    manager: Optional[Any] = None,
) -> Dict[str, Any]:
    """Manage schedule lifecycle."""
    act = action.lower().strip()
    sched = get_publishing_schedule(schedule_name=schedule_name, manager=manager)

    if not sched and schedule_name == "default":
        # Auto-create default schedule
        from database.models import upsert_publishing_schedule
        upsert_publishing_schedule(
            schedule_name="default",
            cadence="one_per_day",
            preferred_times=["10:00"],
            is_paused=False,
            manager=manager,
        )
        sched = get_publishing_schedule(schedule_name="default", manager=manager)

    if not sched:
        return {
            "success": False,
            "schedule_name": schedule_name,
            "action": act,
            "is_paused": False,
            "cadence": None,
            "message": f"Schedule '{schedule_name}' does not exist.",
            "error": "SCHEDULE_NOT_FOUND",
        }

    if act == "pause":
        set_schedule_paused(schedule_name=schedule_name, paused=True, manager=manager)
        return {
            "success": True,
            "schedule_name": schedule_name,
            "action": "pause",
            "is_paused": True,
            "cadence": sched["cadence"],
            "message": f"Schedule '{schedule_name}' has been paused. All publishing is suspended.",
            "error": None,
        }
    elif act == "resume":
        set_schedule_paused(schedule_name=schedule_name, paused=False, manager=manager)
        return {
            "success": True,
            "schedule_name": schedule_name,
            "action": "resume",
            "is_paused": False,
            "cadence": sched["cadence"],
            "message": f"Schedule '{schedule_name}' has been resumed.",
            "error": None,
        }
    elif act == "status":
        state_str = "PAUSED" if sched["is_paused"] else "ACTIVE"
        return {
            "success": True,
            "schedule_name": schedule_name,
            "action": "status",
            "is_paused": sched["is_paused"],
            "cadence": sched["cadence"],
            "message": f"Schedule '{schedule_name}' is currently {state_str} (cadence: {sched['cadence']}, times: {sched['preferred_times']}).",
            "error": None,
        }
    else:
        return {
            "success": False,
            "schedule_name": schedule_name,
            "action": act,
            "is_paused": sched["is_paused"],
            "cadence": sched["cadence"],
            "message": f"Invalid action '{action}'. Use 'pause', 'resume', or 'status'.",
            "error": "INVALID_ACTION",
        }
