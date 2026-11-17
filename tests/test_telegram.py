"""Tests for Telegram bot interface, authentication, and handlers."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agent.config import settings
from agent.orchestrator import Orchestrator
from agent.router import SkillRouter
from agent.llm import MockLLMClient
from telegram_bot.handlers import TelegramHandlers, authorized_only
from telegram_bot.keyboards import get_main_menu_keyboard
from telegram_bot.bot import CaspianTelegramBot


def _run_async(coro):
    """Helper to run async handler in test."""
    return asyncio.run(coro)


@pytest.fixture
def mock_telegram_update():
    """Create a mock Telegram update."""
    update = MagicMock()
    user = MagicMock()
    user.id = 123456789
    user.first_name = "Researcher"
    user.username = "caspian_user"
    update.effective_user = user

    message = MagicMock()
    message.reply_text = AsyncMock()
    message.text = "Hello Caspian"
    update.effective_message = message

    return update


@pytest.fixture
def custom_handlers():
    """Create handlers with mock LLM and test orchestrator."""
    mock_llm = MockLLMClient()
    router = SkillRouter(llm_client=mock_llm)
    orch = Orchestrator(router=router, llm_client=mock_llm)
    return TelegramHandlers(orchestrator=orch)


def test_main_menu_keyboard():
    keyboard = get_main_menu_keyboard()
    assert keyboard is not None
    assert len(keyboard.keyboard) == 2
    assert keyboard.keyboard[0][0].text == "Check Caspian"


def test_unauthorized_user_rejection(mock_telegram_update, custom_handlers):
    # Set authorized user ID to a DIFFERENT user ID
    with patch.object(settings, "telegram_authorized_user_id", "999999999"):
        _run_async(custom_handlers.handle_start(mock_telegram_update, MagicMock()))

        # Should reply with unauthorized warning
        mock_telegram_update.effective_message.reply_text.assert_called_once()
        call_arg = mock_telegram_update.effective_message.reply_text.call_args[0][0]
        assert "Unauthorized access" in call_arg


def test_authorized_user_start_command(mock_telegram_update, custom_handlers):
    # Set authorized user ID to match update.effective_user.id
    with patch.object(settings, "telegram_authorized_user_id", "123456789"):
        _run_async(custom_handlers.handle_start(mock_telegram_update, MagicMock()))

        mock_telegram_update.effective_message.reply_text.assert_called_once()
        call_arg = mock_telegram_update.effective_message.reply_text.call_args[0][0]
        assert "Welcome Researcher to **Project Caspian Agent**" in call_arg


def test_help_command(mock_telegram_update, custom_handlers):
    with patch.object(settings, "telegram_authorized_user_id", "123456789"):
        _run_async(custom_handlers.handle_help(mock_telegram_update, MagicMock()))

        mock_telegram_update.effective_message.reply_text.assert_called_once()
        call_arg = mock_telegram_update.effective_message.reply_text.call_args[0][0]
        assert "Project Caspian Agent Help" in call_arg
        assert "/status" in call_arg


def test_status_command(mock_telegram_update, custom_handlers):
    with patch.object(settings, "telegram_authorized_user_id", "123456789"):
        _run_async(custom_handlers.handle_status(mock_telegram_update, MagicMock()))

        mock_telegram_update.effective_message.reply_text.assert_called_once()
        call_arg = mock_telegram_update.effective_message.reply_text.call_args[0][0]
        assert "System Operational Status" in call_arg
        assert "Registered Skills" in call_arg
        assert "Registered Tools" in call_arg


def test_message_handler_skill_activation(mock_telegram_update, custom_handlers):
    with patch.object(settings, "telegram_authorized_user_id", "123456789"):
        mock_telegram_update.effective_message.text = "check Caspian repository updates"
        _run_async(custom_handlers.handle_message(mock_telegram_update, MagicMock()))

        mock_telegram_update.effective_message.reply_text.assert_called_once()
        call_arg = mock_telegram_update.effective_message.reply_text.call_args[0][0]
        assert "Skill Activated" in call_arg
        assert "Caspian Research" in call_arg


def test_message_handler_unknown_intent(mock_telegram_update, custom_handlers):
    with patch.object(settings, "telegram_authorized_user_id", "123456789"):
        mock_telegram_update.effective_message.text = "write a poem about sailboats"
        _run_async(custom_handlers.handle_message(mock_telegram_update, MagicMock()))

        mock_telegram_update.effective_message.reply_text.assert_called_once()
        call_arg = mock_telegram_update.effective_message.reply_text.call_args[0][0]
        assert "not sure how to handle" in call_arg


def test_bot_application_builder_missing_token(monkeypatch):
    monkeypatch.setattr(settings, "telegram_bot_token", None)
    bot = CaspianTelegramBot(token=None)
    with pytest.raises(ValueError) as exc:
        bot.build_application()
    assert "token is required" in str(exc.value)


def test_bot_application_builder_with_token():
    bot = CaspianTelegramBot(token="123456789:ABCdefGHIjklMNOpqrsTUVwxyz123456789")
    app = bot.build_application()
    assert app is not None
    assert len(app.handlers) >= 1
