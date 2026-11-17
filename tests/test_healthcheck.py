"""Unit tests for container healthcheck script."""

import json
from datetime import datetime, timezone, timedelta
from scripts.healthcheck import check_health
from database.models import set_system_setting


def test_healthcheck_success(temp_db):
    """Verify healthcheck passes when database and heartbeat are healthy."""
    now_iso = datetime.now(timezone.utc).isoformat()
    set_system_setting(
        "health_heartbeat",
        json.dumps({"status": "HEALTHY", "timestamp": now_iso}),
    )

    exit_code = check_health()
    assert exit_code == 0


def test_healthcheck_stale_heartbeat(temp_db):
    """Verify healthcheck warns or fails when heartbeat is older than threshold."""
    old_time = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
    set_system_setting(
        "health_heartbeat",
        json.dumps({"status": "HEALTHY", "timestamp": old_time}),
    )

    exit_code = check_health()
    assert exit_code == 1
