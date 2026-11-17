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

CREATE TABLE IF NOT EXISTS caspian_knowledge (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    experiment_id TEXT,
    commit_hash TEXT,
    findings TEXT,
    limitations TEXT,
    disclosure_status TEXT NOT NULL DEFAULT 'REVIEW_REQUIRED',
    raw_content TEXT,
    source_file TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS external_ai_knowledge (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    source_url TEXT UNIQUE NOT NULL,
    source_name TEXT NOT NULL,
    publication_date TEXT,
    research_type TEXT NOT NULL,
    topic TEXT NOT NULL,
    summary TEXT,
    central_contribution TEXT,
    findings TEXT,
    relevance_score REAL DEFAULT 0.5,
    importance_score REAL DEFAULT 0.5,
    raw_content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS daily_briefings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    briefing_date TEXT NOT NULL,
    developments_json TEXT NOT NULL,
    key_takeaways_json TEXT,
    caspian_relevance_json TEXT,
    sources_json TEXT,
    formatted_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS content_drafts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    draft_id TEXT UNIQUE NOT NULL,
    content_type TEXT NOT NULL,
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    sources_json TEXT,
    verification_status TEXT NOT NULL DEFAULT 'PENDING',
    disclosure_status TEXT NOT NULL DEFAULT 'REVIEW_REQUIRED',
    approval_status TEXT NOT NULL DEFAULT 'PENDING',
    scheduled_time TIMESTAMP,
    publication_status TEXT NOT NULL DEFAULT 'DRAFT',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_draft_id ON content_drafts(draft_id);
CREATE INDEX IF NOT EXISTS idx_draft_approval ON content_drafts(approval_status);
CREATE INDEX IF NOT EXISTS idx_draft_publication ON content_drafts(publication_status);
CREATE INDEX IF NOT EXISTS idx_briefing_date ON daily_briefings(briefing_date);
CREATE INDEX IF NOT EXISTS idx_external_url ON external_ai_knowledge(source_url);
CREATE INDEX IF NOT EXISTS idx_external_topic ON external_ai_knowledge(topic);
CREATE INDEX IF NOT EXISTS idx_external_type ON external_ai_knowledge(research_type);
CREATE INDEX IF NOT EXISTS idx_caspian_experiment ON caspian_knowledge(experiment_id);
CREATE INDEX IF NOT EXISTS idx_caspian_commit ON caspian_knowledge(commit_hash);
CREATE INDEX IF NOT EXISTS idx_caspian_disclosure ON caspian_knowledge(disclosure_status);
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


def save_caspian_research(
    title: str,
    experiment_id: Optional[str] = None,
    commit_hash: Optional[str] = None,
    findings: Optional[str] = None,
    limitations: Optional[str] = None,
    disclosure_status: str = "REVIEW_REQUIRED",
    raw_content: Optional[str] = None,
    source_file: Optional[str] = None,
    manager: Optional[DatabaseManager] = None,
) -> int:
    """Store structured Caspian research context."""
    mgr = manager or db_manager
    query = """
    INSERT INTO caspian_knowledge (
        title, experiment_id, commit_hash, findings, limitations,
        disclosure_status, raw_content, source_file
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """
    with mgr.connection() as conn:
        cursor = conn.execute(
            query,
            (
                title,
                experiment_id,
                commit_hash,
                findings,
                limitations,
                disclosure_status,
                raw_content,
                source_file,
            ),
        )
        return cursor.lastrowid


def retrieve_caspian_context(
    query_text: Optional[str] = None,
    disclosure_filter: Optional[str] = None,
    limit: int = 10,
    manager: Optional[DatabaseManager] = None,
) -> List[Dict[str, Any]]:
    """Query stored Caspian research history."""
    mgr = manager or db_manager
    sql = "SELECT * FROM caspian_knowledge WHERE 1=1"
    params: List[Any] = []

    if disclosure_filter:
        sql += " AND disclosure_status = ?"
        params.append(disclosure_filter)

    if query_text:
        sql += " AND (title LIKE ? OR findings LIKE ? OR raw_content LIKE ?)"
        term = f"%{query_text}%"
        params.extend([term, term, term])

    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    with mgr.connection() as conn:
        cur = conn.execute(sql, tuple(params))
        return [dict(row) for row in cur.fetchall()]


def save_external_knowledge(
    title: str,
    source_url: str,
    source_name: str,
    publication_date: Optional[str] = None,
    research_type: str = "preprint",
    topic: str = "general_ai",
    summary: Optional[str] = None,
    central_contribution: Optional[str] = None,
    findings: Optional[str] = None,
    relevance_score: float = 0.5,
    importance_score: float = 0.5,
    raw_content: Optional[str] = None,
    manager: Optional[DatabaseManager] = None,
) -> int:
    """Store structured external AI intelligence record."""
    mgr = manager or db_manager
    query = """
    INSERT INTO external_ai_knowledge (
        title, source_url, source_name, publication_date, research_type,
        topic, summary, central_contribution, findings, relevance_score,
        importance_score, raw_content
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(source_url) DO UPDATE SET
        summary=excluded.summary,
        relevance_score=excluded.relevance_score,
        importance_score=excluded.importance_score;
    """
    with mgr.connection() as conn:
        cursor = conn.execute(
            query,
            (
                title,
                source_url,
                source_name,
                publication_date,
                research_type,
                topic,
                summary,
                central_contribution,
                findings,
                relevance_score,
                importance_score,
                raw_content,
            ),
        )
        return cursor.lastrowid


def search_external_knowledge(
    query_text: Optional[str] = None,
    topic: Optional[str] = None,
    research_type: Optional[str] = None,
    limit: int = 10,
    manager: Optional[DatabaseManager] = None,
) -> List[Dict[str, Any]]:
    """Search stored external AI intelligence."""
    mgr = manager or db_manager
    sql = "SELECT * FROM external_ai_knowledge WHERE 1=1"
    params: List[Any] = []

    if topic:
        sql += " AND topic LIKE ?"
        params.append(f"%{topic}%")

    if research_type:
        sql += " AND research_type = ?"
        params.append(research_type)

    if query_text:
        sql += " AND (title LIKE ? OR summary LIKE ? OR central_contribution LIKE ?)"
        term = f"%{query_text}%"
        params.extend([term, term, term])

    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    with mgr.connection() as conn:
        cur = conn.execute(sql, tuple(params))
        return [dict(row) for row in cur.fetchall()]


def is_source_url_stored(url: str, manager: Optional[DatabaseManager] = None) -> bool:
    """Check if a source URL is already stored."""
    mgr = manager or db_manager
    query = "SELECT 1 FROM external_ai_knowledge WHERE source_url = ? LIMIT 1;"
    with mgr.connection() as conn:
        cur = conn.execute(query, (url.strip(),))
        return cur.fetchone() is not None


def save_daily_briefing(
    briefing_date: str,
    developments: List[Dict[str, Any]],
    key_takeaways: List[str],
    caspian_relevance: List[Dict[str, Any]],
    sources: List[str],
    formatted_text: str,
    manager: Optional[DatabaseManager] = None,
) -> int:
    """Save generated daily briefing to database."""
    mgr = manager or db_manager
    query = """
    INSERT INTO daily_briefings (
        briefing_date, developments_json, key_takeaways_json,
        caspian_relevance_json, sources_json, formatted_text
    ) VALUES (?, ?, ?, ?, ?, ?);
    """
    with mgr.connection() as conn:
        cur = conn.execute(
            query,
            (
                briefing_date,
                json.dumps(developments),
                json.dumps(key_takeaways),
                json.dumps(caspian_relevance),
                json.dumps(sources),
                formatted_text,
            ),
        )
        return cur.lastrowid


def get_latest_daily_briefing(manager: Optional[DatabaseManager] = None) -> Optional[Dict[str, Any]]:
    """Retrieve the most recent daily briefing."""
    mgr = manager or db_manager
    query = "SELECT * FROM daily_briefings ORDER BY id DESC LIMIT 1;"
    with mgr.connection() as conn:
        cur = conn.execute(query)
        row = cur.fetchone()
        if not row:
            return None
        res = dict(row)
        res["developments"] = json.loads(res["developments_json"])
        res["key_takeaways"] = json.loads(res["key_takeaways_json"]) if res["key_takeaways_json"] else []
        res["caspian_relevance"] = json.loads(res["caspian_relevance_json"]) if res["caspian_relevance_json"] else []
        res["sources"] = json.loads(res["sources_json"]) if res["sources_json"] else []
        return res


def save_content_draft(
    draft_id: str,
    content_type: str,
    content: str,
    content_hash: str,
    sources: List[str],
    verification_status: str = "PENDING",
    disclosure_status: str = "REVIEW_REQUIRED",
    approval_status: str = "PENDING",
    scheduled_time: Optional[str] = None,
    publication_status: str = "DRAFT",
    manager: Optional[DatabaseManager] = None,
) -> int:
    """Save content draft with cryptographic content hash binding."""
    mgr = manager or db_manager
    query = """
    INSERT INTO content_drafts (
        draft_id, content_type, content, content_hash, sources_json,
        verification_status, disclosure_status, approval_status,
        scheduled_time, publication_status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(draft_id) DO UPDATE SET
        content=excluded.content,
        content_hash=excluded.content_hash,
        verification_status=excluded.verification_status,
        disclosure_status=excluded.disclosure_status,
        approval_status=excluded.approval_status,
        updated_at=CURRENT_TIMESTAMP;
    """
    with mgr.connection() as conn:
        cur = conn.execute(
            query,
            (
                draft_id,
                content_type,
                content,
                content_hash,
                json.dumps(sources),
                verification_status,
                disclosure_status,
                approval_status,
                scheduled_time,
                publication_status,
            ),
        )
        return cur.lastrowid


def get_content_draft(draft_id: str, manager: Optional[DatabaseManager] = None) -> Optional[Dict[str, Any]]:
    """Retrieve content draft by draft_id."""
    mgr = manager or db_manager
    query = "SELECT * FROM content_drafts WHERE draft_id = ? LIMIT 1;"
    with mgr.connection() as conn:
        cur = conn.execute(query, (draft_id,))
        row = cur.fetchone()
        if not row:
            return None
        res = dict(row)
        res["sources"] = json.loads(res["sources_json"]) if res["sources_json"] else []
        return res


def update_draft_approval(
    draft_id: str,
    new_approval_status: str,
    expected_content_hash: str,
    manager: Optional[DatabaseManager] = None,
) -> bool:
    """
    Update draft approval status.
    Strictly verifies that the draft's content has not changed since approval.
    """
    mgr = manager or db_manager
    draft = get_content_draft(draft_id, manager=mgr)
    if not draft:
        return False

    # Security check: any modification to content invalidates previous approval
    if draft["content_hash"] != expected_content_hash:
        return False

    query = """
    UPDATE content_drafts
    SET approval_status = ?, updated_at = CURRENT_TIMESTAMP
    WHERE draft_id = ? AND content_hash = ?;
    """
    with mgr.connection() as conn:
        cur = conn.execute(query, (new_approval_status, draft_id, expected_content_hash))
        return cur.rowcount > 0
