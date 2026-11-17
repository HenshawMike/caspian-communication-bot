"""Tests for structured logging and secret scrubbing."""

import logging
from agent.logging_config import redact_secrets, setup_logger, SecretRedactingFilter


def test_redact_secrets_google_api_key():
    raw = "Connecting with key AIzaSyA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q"
    cleaned = redact_secrets(raw)
    assert "***REDACTED_GOOGLE_KEY***" in cleaned
    assert "A1B2C3D4" not in cleaned


def test_redact_secrets_telegram_token():
    raw = "Bot token is 123456789:ABCdefGHIjklMNOpqrsTUVwxyz123456789"
    cleaned = redact_secrets(raw)
    assert "***REDACTED_TELEGRAM_TOKEN***" in cleaned
    assert "ABCdefGHI" not in cleaned


def test_redact_secrets_bearer():
    raw = "Authorization: Bearer my_secret_bearer_token_xyz_123456789"
    cleaned = redact_secrets(raw)
    assert "Bearer ***REDACTED***" in cleaned
    assert "my_secret_bearer" not in cleaned


def test_logging_filter():
    filt = SecretRedactingFilter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Executing with key AIzaSyA1B2C3D4E5F6G7H8I9J0K1L2M3N4O5P6Q and token 123456789:ABCdefGHIjklMNOpqrsTUVwxyz123456789",
        args=(),
        exc_info=None,
    )
    filt.filter(record)
    assert "A1B2C3D4" not in record.msg
    assert "ABCdefGHI" not in record.msg
    assert "***REDACTED_GOOGLE_KEY***" in record.msg
    assert "***REDACTED_TELEGRAM_TOKEN***" in record.msg

