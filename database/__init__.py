"""Database package for Project Caspian."""
from database.connection import db_manager, DatabaseManager
from database.models import (
    initialize_database,
    record_audit_log,
    get_audit_logs,
    save_caspian_research,
    retrieve_caspian_context,
    save_external_knowledge,
    search_external_knowledge,
    is_source_url_stored,
)

__all__ = [
    "db_manager",
    "DatabaseManager",
    "initialize_database",
    "record_audit_log",
    "get_audit_logs",
    "save_caspian_research",
    "retrieve_caspian_context",
    "save_external_knowledge",
    "search_external_knowledge",
    "is_source_url_stored",
]
