"""Tool to configure and create publishing schedules."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from agent.tool_registry import register_tool
from agent.permissions import PermissionScope
from database.models import upsert_publishing_schedule


VALID_CADENCES = ["three_per_week", "one_per_day", "three_per_day", "custom"]


class CreateScheduleInput(BaseModel):
    """Input parameters for create_schedule."""
    schedule_name: str = Field(default="default", description="Identifier for this schedule.")
    cadence: str = Field(
        default="one_per_day",
        description="Publishing frequency: 'three_per_week', 'one_per_day', 'three_per_day', or 'custom'.",
    )
    preferred_times: List[str] = Field(
        default_factory=lambda: ["10:00"],
        description="Preferred daily publishing times in 24hr format (e.g. ['09:00', '15:00']).",
    )


class CreateScheduleOutput(BaseModel):
    """Output schema for create_schedule."""
    success: bool
    schedule_name: str
    cadence: str
    preferred_times: List[str]
    message: str
    error: Optional[str] = None


@register_tool(
    name="create_schedule",
    description="Configure publishing cadence (three per week, one per day, three per day, or custom) and publishing times.",
    permission=PermissionScope.SYSTEM_READ,
    args_model=CreateScheduleInput,
    output_model=CreateScheduleOutput,
)
def create_schedule(
    schedule_name: str = "default",
    cadence: str = "one_per_day",
    preferred_times: Optional[List[str]] = None,
    manager: Optional[Any] = None,
) -> Dict[str, Any]:
    """Create or update a publishing schedule."""
    clean_cadence = cadence.lower().strip()
    if clean_cadence not in VALID_CADENCES:
        return {
            "success": False,
            "schedule_name": schedule_name,
            "cadence": cadence,
            "preferred_times": [],
            "message": f"Invalid cadence '{cadence}'. Must be one of: {', '.join(VALID_CADENCES)}",
            "error": "INVALID_CADENCE",
        }

    times = preferred_times or ["10:00"]
    upsert_publishing_schedule(
        schedule_name=schedule_name,
        cadence=clean_cadence,
        preferred_times=times,
        is_paused=False,
        manager=manager,
    )

    return {
        "success": True,
        "schedule_name": schedule_name,
        "cadence": clean_cadence,
        "preferred_times": times,
        "message": f"Publishing schedule '{schedule_name}' configured for '{clean_cadence}' at {times}.",
        "error": None,
    }
