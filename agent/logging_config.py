"""Structured logging with secret redaction for Project Caspian."""

import logging
import json
import re
import os
from typing import Any, Dict


# Patterns to redact
SECRET_PATTERNS = [
    (re.compile(r"AIza[0-9A-Za-z-_]{35}"), "***REDACTED_GOOGLE_KEY***"),
    (re.compile(r"sk-or-[0-9A-Za-z_\-]{30,}"), "***REDACTED_OPENROUTER_KEY***"),
    (re.compile(r"hf_[0-9A-Za-z]{30,}"), "***REDACTED_HF_TOKEN***"),
    (re.compile(r"\d{8,10}:[a-zA-Z0-9_-]{35}"), "***REDACTED_TELEGRAM_TOKEN***"),
    (re.compile(r"(Bearer\s+)[a-zA-Z0-9_\-\.]{20,}", re.IGNORECASE), r"\1***REDACTED***"),
    (re.compile(r"""(["']?[a-zA-Z0-9_]*(?:key|token|secret|password)["']?\s*[:=]\s*["'])([^"',\s]{6,})(["'])""", re.IGNORECASE), r"\1***REDACTED***\3"),
]


def redact_secrets(text: str) -> str:
    """Scrub sensitive secrets from text strings."""
    if not isinstance(text, str):
        return text
    
    redacted = text
    for pattern, replacement in SECRET_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


class SecretRedactingFilter(logging.Filter):
    """Logging filter to mask sensitive keys and tokens from all log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_secrets(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: redact_secrets(str(v)) if isinstance(v, str) else v for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(redact_secrets(str(arg)) if isinstance(arg, str) else arg for arg in record.args)
        return True


class JSONFormatter(logging.Formatter):
    """Structured JSON formatter for production and file logs."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_secrets(record.getMessage()),
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "metadata") and isinstance(record.metadata, dict):
            log_entry["metadata"] = record.metadata
        return json.dumps(log_entry)


def setup_logger(name: str = "caspian", log_level: str = "INFO", json_output: bool = False) -> logging.Logger:
    """Configure and return a sanitized, structured logger."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    logger.propagate = False

    # Avoid duplicate handlers if setup is called multiple times
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.addFilter(SecretRedactingFilter())
        
        if json_output:
            handler.setFormatter(JSONFormatter())
        else:
            handler.setFormatter(
                logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s")
            )
        logger.addHandler(handler)

    return logger


logger = setup_logger()
