"""Tests for Content Generation tools."""

import hashlib
from tools.content.generate_thread import generate_thread
from tools.content.verify_claims import verify_claims
from database.models import save_content_draft, get_content_draft, update_draft_approval


def test_generate_thread():
    points = [
        "First research finding on state representations.",
        "Second experimental finding showing 45% efficiency gains.",
        "Final conclusion and summary.",
    ]
    res = generate_thread(
        topic="Latent Planning",
        key_points=points,
        source_reference="https://arxiv.org/abs/2611.77777",
    )
    assert res["success"] is True
    assert res["total_posts"] == 3
    posts = res["posts"]
    assert posts[0]["text"].startswith("1/3")
    assert posts[1]["text"].startswith("2/3")
    assert posts[2]["text"].startswith("3/3")
    assert "https://arxiv.org/abs/2611.77777" in posts[2]["text"]

    for p in posts:
        assert p["char_count"] <= 280


def test_verify_claims_grounded():
    source = "Our benchmark experiments on SparseGrid demonstrated a 45% reduction in rollout memory."
    claims = ["Benchmark experiments demonstrated a 45% reduction in rollout memory."]

    res = verify_claims(claims=claims, source_text=source)
    assert res["success"] is True
    assert res["is_verified"] is True
    assert res["verification_status"] == "VERIFIED"
    assert len(res["verified_claims"]) == 1
    assert len(res["unsupported_claims"]) == 0


def test_verify_claims_flags_hallucinated_metrics():
    source = "Our benchmark experiments demonstrated a 45% reduction in memory."
    # 99% does not exist in source
    claims = ["Our benchmark experiments demonstrated a 99% reduction in memory."]

    res = verify_claims(claims=claims, source_text=source)
    assert res["is_verified"] is False
    assert res["verification_status"] == "UNSUPPORTED_CLAIMS"
    assert len(res["unsupported_claims"]) == 1


def test_verify_claims_flags_exaggerations():
    source = "The method improves policy performance on synthetic tasks."
    claims = ["This is a completely flawless algorithm that solves all problems."]

    res = verify_claims(claims=claims, source_text=source)
    assert res["is_verified"] is False
    assert res["verification_status"] == "UNSUPPORTED_CLAIMS"


def test_draft_hash_binding_and_approval(temp_db):
    content = "Project Caspian Update: Latent world models achieve 40% memory reduction."
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    save_content_draft(
        draft_id="DRAFT-TEST-001",
        content_type="single_post",
        content=content,
        content_hash=content_hash,
        sources=["https://arxiv.org/abs/2611.88888"],
        manager=temp_db,
    )

    draft = get_content_draft("DRAFT-TEST-001", manager=temp_db)
    assert draft is not None
    assert draft["approval_status"] == "PENDING"

    # Attempt approval with matching hash
    ok = update_draft_approval("DRAFT-TEST-001", "APPROVED", content_hash, manager=temp_db)
    assert ok is True

    updated = get_content_draft("DRAFT-TEST-001", manager=temp_db)
    assert updated["approval_status"] == "APPROVED"

    # Attempt approval with mismatched hash (content was tampered with)
    tampered_hash = hashlib.sha256(b"Tampered content").hexdigest()
    failed_ok = update_draft_approval("DRAFT-TEST-001", "APPROVED", tampered_hash, manager=temp_db)
    assert failed_ok is False
