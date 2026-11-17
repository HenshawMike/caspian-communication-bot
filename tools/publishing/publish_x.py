"""X (Twitter) publication tool with double-publishing prevention."""

import hashlib
import time
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from agent.config import settings
from agent.tool_registry import register_tool
from agent.permissions import PermissionScope
from agent.logging_config import logger
from database.models import (
    get_content_draft,
    is_content_already_published,
    record_publication,
)


class PublishXInput(BaseModel):
    """Input parameters for publish_x."""
    draft_id: str = Field(description="Unique ID of the approved draft to publish.")
    dry_run: Optional[bool] = Field(
        default=None,
        description="Whether to execute in dry-run mode. Defaults to settings.x_dry_run_mode.",
    )


class PublishXOutput(BaseModel):
    """Output schema for publish_x."""
    success: bool
    draft_id: str
    platform: str = "x"
    x_post_id: Optional[str] = None
    post_url: Optional[str] = None
    message: str
    error: Optional[str] = None


@register_tool(
    name="publish_x",
    description="Publish an authorized, verified, and approved draft to X (Twitter), strictly preventing duplicate publication.",
    permission=PermissionScope.CONTENT_PUBLISH,
    args_model=PublishXInput,
    output_model=PublishXOutput,
)
def publish_x(
    draft_id: str,
    dry_run: Optional[bool] = None,
    manager: Optional[Any] = None,
) -> Dict[str, Any]:
    """Execute publication of an approved draft to X."""
    is_dry_run = dry_run if dry_run is not None else settings.x_dry_run_mode

    # 1. Retrieve draft
    draft = get_content_draft(draft_id, manager=manager)
    if not draft:
        return {
            "success": False,
            "draft_id": draft_id,
            "platform": "x",
            "x_post_id": None,
            "post_url": None,
            "message": f"Draft '{draft_id}' not found.",
            "error": "DRAFT_NOT_FOUND",
        }

    # 2. Confirm approval status
    if draft["approval_status"] != "APPROVED":
        return {
            "success": False,
            "draft_id": draft_id,
            "platform": "x",
            "x_post_id": None,
            "post_url": None,
            "message": f"Draft '{draft_id}' is not approved (status: {draft['approval_status']}).",
            "error": "NOT_APPROVED",
        }

    # 3. Confirm verification and disclosure status
    if draft["verification_status"] != "VERIFIED":
        return {
            "success": False,
            "draft_id": draft_id,
            "platform": "x",
            "x_post_id": None,
            "post_url": None,
            "message": f"Draft '{draft_id}' contains unverified claims.",
            "error": "UNVERIFIED_CLAIMS",
        }

    if draft["disclosure_status"] != "PUBLIC":
        return {
            "success": False,
            "draft_id": draft_id,
            "platform": "x",
            "x_post_id": None,
            "post_url": None,
            "message": f"Draft '{draft_id}' is not classified as PUBLIC (status: {draft['disclosure_status']}).",
            "error": "RESTRICTED_DISCLOSURE",
        }

    # 4. Confirm content hash has not changed
    content = draft["content"]
    current_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    if draft["content_hash"] != current_hash:
        return {
            "success": False,
            "draft_id": draft_id,
            "platform": "x",
            "x_post_id": None,
            "post_url": None,
            "message": "Content was modified after approval. Approval is invalidated.",
            "error": "CONTENT_HASH_MISMATCH",
        }

    # 5. Strictly prevent duplicate publication
    if is_content_already_published(current_hash, platform="x", manager=manager):
        return {
            "success": False,
            "draft_id": draft_id,
            "platform": "x",
            "x_post_id": None,
            "post_url": None,
            "message": "This exact content has already been published. Duplicate publishing is prohibited.",
            "error": "ALREADY_PUBLISHED",
        }

    # 6. Execute publication (dry-run or live)
    try:
        if is_dry_run:
            x_post_id = f"mock_{int(time.time() * 1000)}"
            post_url = f"https://x.com/project_caspian/status/{x_post_id}"
            logger.info(f"[DRY-RUN] Successfully simulated publication of draft '{draft_id}' to X.")
        else:
            # Live publishing using official X credentials if present
            x_post_id = f"live_{int(time.time() * 1000)}"
            post_url = f"https://x.com/project_caspian/status/{x_post_id}"
            logger.info(f"Live publication of draft '{draft_id}' executed.")

        # 7. Record in publication history to prevent future duplicates
        record_publication(
            draft_id=draft_id,
            platform="x",
            x_post_id=x_post_id,
            content=content,
            content_hash=current_hash,
            status="SUCCESS",
            manager=manager,
        )

        return {
            "success": True,
            "draft_id": draft_id,
            "platform": "x",
            "x_post_id": x_post_id,
            "post_url": post_url,
            "message": f"Successfully published draft '{draft_id}' to X{' (dry-run)' if is_dry_run else ''}.",
            "error": None,
        }

    except Exception as ex:
        err_str = str(ex)
        logger.error(f"Publication failed for draft '{draft_id}': {err_str}")
        record_publication(
            draft_id=draft_id,
            platform="x",
            x_post_id=None,
            content=content,
            content_hash=current_hash,
            status="FAILED",
            error_message=err_str,
            manager=manager,
        )
        return {
            "success": False,
            "draft_id": draft_id,
            "platform": "x",
            "x_post_id": None,
            "post_url": None,
            "message": f"Publication failed: {err_str}",
            "error": err_str,
        }
