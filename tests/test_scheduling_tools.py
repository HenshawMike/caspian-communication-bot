"""Tests for Publishing Scheduling tools."""

import hashlib
from tools.scheduling.create_schedule import create_schedule
from tools.scheduling.manage_schedule import manage_schedule
from tools.scheduling.execute_schedule import execute_schedule
from database.models import save_content_draft
from tools.publishing.queue_post import queue_post


def test_create_schedule_valid(temp_db):
    res = create_schedule(
        schedule_name="test_sched",
        cadence="three_per_week",
        preferred_times=["09:00", "15:00"],
        manager=temp_db,
    )
    assert res["success"] is True
    assert res["cadence"] == "three_per_week"


def test_create_schedule_invalid_cadence(temp_db):
    res = create_schedule(
        schedule_name="bad_sched",
        cadence="invalid_cadence",
        manager=temp_db,
    )
    assert res["success"] is False
    assert res["error"] == "INVALID_CADENCE"


def test_manage_schedule_pause_and_resume(temp_db):
    create_schedule(schedule_name="ops_sched", cadence="one_per_day", manager=temp_db)

    # Pause
    pause_res = manage_schedule(schedule_name="ops_sched", action="pause", manager=temp_db)
    assert pause_res["success"] is True
    assert pause_res["is_paused"] is True

    # Status
    stat_res = manage_schedule(schedule_name="ops_sched", action="status", manager=temp_db)
    assert stat_res["is_paused"] is True
    assert "PAUSED" in stat_res["message"]

    # Resume
    resume_res = manage_schedule(schedule_name="ops_sched", action="resume", manager=temp_db)
    assert resume_res["is_paused"] is False


def test_execute_schedule_publishes_queued_draft(temp_db):
    create_schedule(schedule_name="exec_sched", cadence="one_per_day", manager=temp_db)

    content = "Scheduled research finding ready for publication."
    c_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    save_content_draft(
        draft_id="DRAFT-SCHED-01",
        content_type="single_post",
        content=content,
        content_hash=c_hash,
        sources=[],
        verification_status="VERIFIED",
        disclosure_status="PUBLIC",
        approval_status="APPROVED",
        publication_status="QUEUED",
        manager=temp_db,
    )

    exec_res = execute_schedule(schedule_name="exec_sched", max_items=1, manager=temp_db)
    assert exec_res["success"] is True
    assert exec_res["published_count"] == 1
    assert exec_res["published_items"][0]["draft_id"] == "DRAFT-SCHED-01"


def test_execute_schedule_strictly_skips_when_paused(temp_db):
    create_schedule(schedule_name="paused_sched", cadence="one_per_day", manager=temp_db)
    manage_schedule(schedule_name="paused_sched", action="pause", manager=temp_db)

    content = "Post waiting for release."
    c_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    save_content_draft(
        draft_id="DRAFT-SCHED-02",
        content_type="single_post",
        content=content,
        content_hash=c_hash,
        sources=[],
        verification_status="VERIFIED",
        disclosure_status="PUBLIC",
        approval_status="APPROVED",
        publication_status="QUEUED",
        manager=temp_db,
    )

    # Must NOT publish when paused
    exec_res = execute_schedule(schedule_name="paused_sched", max_items=1, manager=temp_db)
    assert exec_res["success"] is True
    assert exec_res["is_paused"] is True
    assert exec_res["published_count"] == 0
    assert "paused" in exec_res["message"]
