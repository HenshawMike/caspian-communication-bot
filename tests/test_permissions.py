"""Tests for permission architecture and verification."""

import pytest
from agent.permissions import (
    PermissionContext,
    PermissionScope,
    PermissionDeniedError,
    create_default_context,
)


def test_permission_context_add_and_check():
    ctx = PermissionContext(user_id="user123")
    assert not ctx.has_scope(PermissionScope.REPOSITORY_READ)

    ctx.add_scope(PermissionScope.REPOSITORY_READ)
    assert ctx.has_scope(PermissionScope.REPOSITORY_READ)
    assert ctx.has_scope("repository_read")


def test_permission_verification_passes():
    ctx = PermissionContext()
    ctx.add_scope(PermissionScope.SYSTEM_READ)
    # Should not raise
    ctx.verify_permission(PermissionScope.SYSTEM_READ)


def test_permission_verification_fails():
    ctx = PermissionContext()
    ctx.add_scope(PermissionScope.SYSTEM_READ)

    with pytest.raises(PermissionDeniedError) as exc_info:
        ctx.verify_permission(PermissionScope.CONTENT_PUBLISH)

    assert "Permission denied" in str(exc_info.value)
    assert exc_info.value.required == "content_publish"


def test_default_context_excludes_publish():
    ctx = create_default_context(user_id="user456")
    assert ctx.has_scope(PermissionScope.SYSTEM_READ)
    assert ctx.has_scope(PermissionScope.REPOSITORY_READ)
    assert ctx.has_scope(PermissionScope.CONTENT_GENERATE)
    # Critical security rule: content_publish must NOT be present by default
    assert not ctx.has_scope(PermissionScope.CONTENT_PUBLISH)
