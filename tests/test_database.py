"""Tests for SQLite database and audit logging."""

from database.models import record_audit_log, get_audit_logs


def test_database_initialization_and_audit(temp_db):
    row_id = record_audit_log(
        tool_name="system_ping",
        success=True,
        duration_ms=12.4,
        caller_id="test_user",
        active_skill="caspian_research",
        input_params={"param1": "value1"},
        output_data={"status": "healthy"},
        manager=temp_db,
    )
    assert row_id is not None
    assert row_id > 0

    logs = get_audit_logs(tool_name="system_ping", limit=10, manager=temp_db)
    assert len(logs) == 1
    log = logs[0]
    assert log["tool_name"] == "system_ping"
    assert log["success"] == 1
    assert log["caller_id"] == "test_user"
    assert "param1" in log["input_params"]


def test_audit_log_scrubs_secrets_in_inputs(temp_db):
    record_audit_log(
        tool_name="system_ping",
        success=False,
        duration_ms=5.0,
        input_params={"api_key": "AIzaSySecretApiKey123456789012345678"},
        error_message="Failed with token: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz123456789",
        manager=temp_db,
    )

    logs = get_audit_logs(tool_name="system_ping", limit=5, manager=temp_db)
    assert len(logs) == 1
    entry = logs[0]
    assert "AIzaSySecretApiKey" not in entry["input_params"]
    assert "***REDACTED" in entry["input_params"]
    assert "ABCdefGHI" not in entry["error_message"]
    assert "***REDACTED_TELEGRAM_TOKEN***" in entry["error_message"]
