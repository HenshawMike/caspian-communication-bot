"""Database schema models and repository functions."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from database.connection import db_manager, DatabaseManager
from agent.logging_config import redact_secrets


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_name TEXT NOT NULL,
    success BOOLEAN NOT NULL,
    duration_ms REAL NOT NULL,
    caller_id TEXT,
    active_skill TEXT,
    input_params TEXT,
    output_data TEXT,
    error_code TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS session_state (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    active_skill TEXT,
    state_json TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS system_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_tool_name ON audit_logs(tool_name);
CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_logs(created_at);
"""


def initialize_database(manager: Optional[DatabaseManager] = None) -> None:
    """Execute initial schema creation."""
    mgr = manager or db_manager
    with mgr.connection() as conn:
        conn.executescript(SCHEMA_SQL)


def record_audit_log(
    tool_name: str,
    success: bool,
    duration_ms: float,
    caller_id: Optional[str] = None,
    active_skill: Optional[str] = None,
    input_params: Optional[Dict[str, Any]] = None,
    output_data: Optional[Any] = None,
    error_code: Optional[str] = None,
    error_message: Optional[str] = None,
    manager: Optional[DatabaseManager] = None,
) -> int:
    """Record a tool execution to the audit log with secret redaction."""
    mgr = manager or db_manager
    clean_inputs = redact_secrets(json.dumps(input_params)) if input_params is not None else None
    clean_output = redact_secrets(json.dumps(output_data)) if output_data is not None else None
    clean_error = redact_secrets(error_message) if error_message is not None else None

    query = """
    INSERT INTO audit_logs (
        tool_name, success, duration_ms, caller_id, active_skill,
        input_params, output_data, error_code, error_message
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """
    with mgr.connection() as conn:
        cursor = conn.execute(
            query,
            (
                tool_name,
                success,
                duration_ms,
                caller_id,
                active_skill,
                clean_inputs,
                clean_output,
                error_code,
                clean_error,
            ),
        )
        return cursor.lastrowid


def get_audit_logs(
    tool_name: Optional[str] = None,
    limit: int = 50,
    manager: Optional[DatabaseManager] = None,
) -> List[Dict[str, Any]]:
    """Retrieve recent audit logs."""
    mgr = manager or db_manager
    with mgr.connection() as conn:
        if tool_name:
            cur = conn.execute(
                "SELECT * FROM audit_logs WHERE tool_name = ? ORDER BY id DESC LIMIT ?",
                (tool_name, limit),
            )
        else:
            cur = conn.execute(
                "SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?",
                (limit,),
            )
        return [dict(row) for row in cur.fetchall()]
