"""Tests for X Publishing tools."""

import hashlib
from tools.publishing.publish_x import publish_x
from tools.publishing.queue_post import queue_post
from tools.publishing.publication_history import publication_history
from database.models import save_content_draft, get_content_draft


def test_publish_x_approved_draft_success(temp_db):
    content = "Project Caspian Update: Empirical results in latent planning."
    c_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    save_content_draft(
        draft_id="DRAFT-PUB-001",
        content_type="single_post",
        content=content,
        content_hash=c_hash,
        sources=["https://arxiv.org/abs/2611.99999"],
        verification_status="VERIFIED",
        disclosure_status="PUBLIC",
        approval_status="APPROVED",
        manager=temp_db,
    )

    res = publish_x("DRAFT-PUB-001", dry_run=True, manager=temp_db)
    assert res["success"] is True
    assert res["x_post_id"] is not None
    assert "https://x.com/" in res["post_url"]

    # Verify content_drafts status updated to PUBLISHED
    draft = get_content_draft("DRAFT-PUB-001", manager=temp_db)
    assert draft["publication_status"] == "PUBLISHED"


def test_publish_x_rejects_unapproved_draft(temp_db):
    content = "Unapproved draft content."
    c_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    save_content_draft(
        draft_id="DRAFT-PUB-002",
        content_type="single_post",
        content=content,
        content_hash=c_hash,
        sources=[],
        verification_status="VERIFIED",
        disclosure_status="PUBLIC",
        approval_status="PENDING",
        manager=temp_db,
    )

    res = publish_x("DRAFT-PUB-002", dry_run=True, manager=temp_db)
    assert res["success"] is False
    assert res["error"] == "NOT_APPROVED"


def test_publish_x_prevents_duplicate_publishing(temp_db):
    content = "Unique research finding to publish once only."
    c_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    save_content_draft(
        draft_id="DRAFT-PUB-003",
        content_type="single_post",
        content=content,
        content_hash=c_hash,
        sources=[],
        verification_status="VERIFIED",
        disclosure_status="PUBLIC",
        approval_status="APPROVED",
        manager=temp_db,
    )

    # First publication succeeds
    first_res = publish_x("DRAFT-PUB-003", dry_run=True, manager=temp_db)
    assert first_res["success"] is True

    # Second publication MUST be rejected
    second_res = publish_x("DRAFT-PUB-003", dry_run=True, manager=temp_db)
    assert second_res["success"] is False
    assert second_res["error"] == "ALREADY_PUBLISHED"
    assert "already been published" in second_res["message"]


def test_queue_post_approved(temp_db):
    content = "Queued post content."
    c_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    save_content_draft(
        draft_id="DRAFT-PUB-004",
        content_type="single_post",
        content=content,
        content_hash=c_hash,
        sources=[],
        verification_status="VERIFIED",
        disclosure_status="PUBLIC",
        approval_status="APPROVED",
        manager=temp_db,
    )

    q_res = queue_post("DRAFT-PUB-004", scheduled_time="2026-11-18T10:00:00Z", manager=temp_db)
    assert q_res["success"] is True

    draft = get_content_draft("DRAFT-PUB-004", manager=temp_db)
    assert draft["publication_status"] == "QUEUED"
    assert draft["scheduled_time"] == "2026-11-18T10:00:00Z"


def test_publication_history(temp_db):
    history_res = publication_history(limit=10, manager=temp_db)
    assert history_res["success"] is True
    assert isinstance(history_res["records"], list)
