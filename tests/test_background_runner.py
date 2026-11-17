"""Unit tests for background scheduling and polling worker."""

import json
from pathlib import Path
from agent.background_runner import BackgroundRunner
from database.models import get_system_setting, save_daily_briefing


def test_background_runner_heartbeat(temp_db, tmp_path):
    """Verify heartbeat writes to database and health file."""
    health_file = tmp_path / "health.json"
    runner = BackgroundRunner(health_file_path=health_file)

    runner.update_heartbeat(status="HEALTHY")

    # Check database
    raw_setting = get_system_setting("health_heartbeat")
    assert raw_setting is not None
    payload = json.loads(raw_setting)
    assert payload["status"] == "HEALTHY"
    assert "timestamp" in payload

    # Check file
    assert health_file.exists()
    with open(health_file, "r") as f:
        file_payload = json.load(f)
        assert file_payload["status"] == "HEALTHY"


def test_background_runner_run_once(temp_db, tmp_path):
    """Verify single execution pass runs without errors."""
    health_file = tmp_path / "health.json"
    runner = BackgroundRunner(health_file_path=health_file)

    res = runner.run_once()
    assert "error" not in res or res.get("error") is None
    assert "timestamp" in res
    assert health_file.exists()


def test_background_runner_briefing_dedup(temp_db, tmp_path):
    """Verify runner does not regenerate daily briefing if already created today."""
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Seed briefing for today
    save_daily_briefing(
        briefing_date=today,
        developments=[],
        key_takeaways=[],
        caspian_relevance=[],
        sources=[],
        formatted_text="Preview",
    )

    runner = BackgroundRunner(briefing_hour_utc=0, health_file_path=tmp_path / "health.json")
    briefing_res = runner.check_and_generate_daily_briefing()
    assert briefing_res is None


def test_background_runner_lifecycle():
    """Verify start and stop methods function cleanly."""
    runner = BackgroundRunner(poll_interval_seconds=1)
    runner.start()
    assert runner._running is True
    assert runner._thread is not None
    runner.stop()
    assert runner._running is False
    assert runner._thread is None
