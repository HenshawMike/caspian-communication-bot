"""Pydantic schemas for skills, tools, and execution envelopes."""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict


class ToolError(BaseModel):
    """Structured tool error information."""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ExecutionMetadata(BaseModel):
    """Metadata recorded for each tool execution."""
    tool_name: str
    duration_ms: float
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    executed_by: Optional[str] = None


class ToolResultEnvelope(BaseModel):
    """Standardized envelope returned by all tool executions."""
    success: bool
    data: Optional[Any] = None
    error: Optional[ToolError] = None
    execution_metadata: ExecutionMetadata


class SkillMetadata(BaseModel):
    """Skill entry in skills/registry.json."""
    id: str
    name: str
    path: str
    description: str
    triggers: List[str] = Field(default_factory=list)
    required_permissions: List[str] = Field(default_factory=list)


class SkillRegistryFile(BaseModel):
    """Structure of skills/registry.json."""
    skills: List[SkillMetadata]


class ParsedSkill(BaseModel):
    """Parsed representation of a SKILL.md file adhering to the 11 mandatory sections."""
    name: str
    identity: str
    activation_conditions: str
    required_inputs: str
    available_tools: List[str]
    tool_routing_rules: str
    execution_workflow: str
    decision_rules: str
    output_contract: str
    failure_handling: str
    restrictions: str
    completion_criteria: str
    raw_markdown: str


class RouteDecision(BaseModel):
    """Result of router evaluation."""
    selected_skill_id: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    reasoning: str
    is_direct_match: bool = False
