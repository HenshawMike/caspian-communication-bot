"""Tests for Caspian Research skill tools."""

import tempfile
from pathlib import Path
from agent.permissions import PermissionContext, PermissionScope, create_default_context
from tools.github.scan_repository import scan_repository
from tools.github.get_commit_details import get_commit_details
from tools.github.extract_reports import extract_reports
from tools.content.check_disclosure import check_disclosure
from tools.content.generate_post import generate_post
from tools.knowledge.retrieve_context import retrieve_context
from database.models import save_caspian_research


def test_scan_repository_on_workspace():
    res = scan_repository()
    assert res["success"] is True
    assert res["latest_commit"] != ""
    assert isinstance(res["new_commits"], list)
    assert isinstance(res["changed_files"], list)


def test_get_commit_details_valid():
    scan_res = scan_repository()
    latest_commit = scan_res["latest_commit"]
    assert latest_commit != ""

    det = get_commit_details(commit_hash=latest_commit)
    assert det["success"] is True
    assert det["commit_hash"] == latest_commit
    assert det["error"] is None


def test_get_commit_details_invalid_hash():
    det = get_commit_details(commit_hash="invalid_hash_xyz!")
    assert det["success"] is False
    assert "Invalid commit hash" in det["error"]


def test_extract_reports(tmp_path):
    # Create sample experiment report
    report_file = tmp_path / "exp_01_world_models.md"
    report_file.write_text(
        """# Latent World Models in Sparse Navigation
<!-- DISCLOSURE: PUBLIC -->
experiment_id: EXP-2026-001

## Hypothesis
Latent state compression improves long-horizon planning efficiency.

## Findings
Compression ratio of 4:1 reduced rollout memory by 62% without degrading policy success rates.

## Limitations
Evaluation was limited to static simulated grid environments.
""",
        encoding="utf-8",
    )

    res = extract_reports(
        file_paths=["exp_01_world_models.md"],
        repository_path=str(tmp_path),
    )
    assert res["success"] is True
    assert res["reports_found"] == 1
    report = res["reports"][0]
    assert report["title"] == "Latent World Models in Sparse Navigation"
    assert report["experiment_id"] == "EXP-2026-001"
    assert report["disclosure_status"] == "PUBLIC"
    assert "62%" in report["findings"]
    assert "static simulated" in report["limitations"]


def test_check_disclosure_public():
    res = check_disclosure(
        content="Public finding: compression reduces memory by 62%.",
        declared_status="PUBLIC",
    )
    assert res["success"] is True
    assert res["status"] == "PUBLIC"
    assert res["is_public_approved"] is True
    assert len(res["reasons"]) == 0


def test_check_disclosure_missing_defaults_to_review():
    res = check_disclosure(
        content="Some research notes with no tag.",
        declared_status=None,
    )
    assert res["success"] is True
    assert res["status"] == "REVIEW_REQUIRED"
    assert res["is_public_approved"] is False
    assert any("defaulted to REVIEW_REQUIRED" in r for r in res["reasons"])


def test_check_disclosure_flags_internal_and_sensitive():
    res = check_disclosure(
        content="Internal finding: connection to 192.168.1.50 with api_key secret123",
        declared_status="PUBLIC",
    )
    assert res["is_public_approved"] is False
    assert res["status"] == "REVIEW_REQUIRED"
    assert any("restricted pattern" in r for r in res["reasons"])


def test_generate_post_formatting():
    res = generate_post(
        topic="Sparse World Models",
        findings="Achieved 62% memory reduction using 4:1 state compression.",
        limitations="Tested only in synthetic benchmarks.",
        source_reference="EXP-2026-001",
    )
    assert res["success"] is True
    assert res["character_count"] <= 280
    assert "Project Caspian Update" in res["post_text"]
    assert "[EXP-2026-001]" in res["post_text"]


def test_retrieve_context_from_db(temp_db):
    save_caspian_research(
        title="Prior Exploration Study",
        experiment_id="EXP-2026-000",
        findings="Intrinsic curiosity baseline.",
        disclosure_status="PUBLIC",
        manager=temp_db,
    )

    items = retrieve_context(query="curiosity", manager=temp_db)["items"]
    assert len(items) == 1
    assert items[0]["title"] == "Prior Exploration Study"
    assert items[0]["experiment_id"] == "EXP-2026-000"
