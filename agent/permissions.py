"""Permission architecture and verification engine."""

from enum import Enum
from typing import Set, Optional
from dataclasses import dataclass, field


class PermissionScope(str, Enum):
    """Authorised permission scopes."""
    SYSTEM_READ = "system_read"
    REPOSITORY_READ = "repository_read"
    EXTERNAL_READ = "external_read"
    KNOWLEDGE_READ = "knowledge_read"
    KNOWLEDGE_WRITE = "knowledge_write"
    CONTENT_GENERATE = "content_generate"
    CONTENT_PUBLISH = "content_publish"


class PermissionDeniedError(Exception):
    """Raised when an operation attempts to run without required permission."""
    def __init__(self, required: str, granted: Set[str], message: Optional[str] = None):
        msg = message or f"Permission denied. Required: '{required}', Granted: {sorted(list(granted))}"
        super().__init__(msg)
        self.required = required
        self.granted = granted


@dataclass
class PermissionContext:
    """Security context holding granted permissions for an execution session."""
    user_id: Optional[str] = None
    active_skill: Optional[str] = None
    granted_scopes: Set[str] = field(default_factory=set)

    def add_scope(self, scope: str | PermissionScope) -> None:
        val = scope.value if isinstance(scope, PermissionScope) else str(scope)
        self.granted_scopes.add(val)

    def remove_scope(self, scope: str | PermissionScope) -> None:
        val = scope.value if isinstance(scope, PermissionScope) else str(scope)
        self.granted_scopes.discard(val)

    def has_scope(self, scope: str | PermissionScope) -> bool:
        val = scope.value if isinstance(scope, PermissionScope) else str(scope)
        return val in self.granted_scopes

    def verify_permission(self, required_scope: str | PermissionScope) -> None:
        val = required_scope.value if isinstance(required_scope, PermissionScope) else str(required_scope)
        if not self.has_scope(val):
            raise PermissionDeniedError(required=val, granted=self.granted_scopes)


def create_default_context(user_id: Optional[str] = None, skill_id: Optional[str] = None) -> PermissionContext:
    """Create default safe permission context with read-only/standard generation permissions."""
    ctx = PermissionContext(user_id=user_id, active_skill=skill_id)
    ctx.add_scope(PermissionScope.SYSTEM_READ)
    ctx.add_scope(PermissionScope.REPOSITORY_READ)
    ctx.add_scope(PermissionScope.EXTERNAL_READ)
    ctx.add_scope(PermissionScope.KNOWLEDGE_READ)
    ctx.add_scope(PermissionScope.KNOWLEDGE_WRITE)
    ctx.add_scope(PermissionScope.CONTENT_GENERATE)
    # CONTENT_PUBLISH is purposefully excluded by default - requires explicit approval
    return ctx
