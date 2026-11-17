"""Telegram Bot application lifecycle and initialization."""

from typing import Optional
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
)

from agent.config import settings
from agent.logging_config import logger
from telegram_bot.handlers import TelegramHandlers, handlers as default_handlers


class CaspianTelegramBot:
    """Manages the lifecycle of the Project Caspian Telegram bot."""

    def __init__(
        self,
        token: Optional[str] = None,
        handlers: Optional[TelegramHandlers] = None,
    ):
        self.token = settings.telegram_bot_token if token is None else token
        self.handlers = handlers or default_handlers
        self.application: Optional[Application] = None

    def build_application(self) -> Application:
        """Configure and return the python-telegram-bot Application."""
        if not self.token:
            raise ValueError(
                "Telegram bot token is required. Set TELEGRAM_BOT_TOKEN in .env or environment."
            )

        app = ApplicationBuilder().token(self.token).build()

        # Register command handlers
        app.add_handler(CommandHandler("start", self.handlers.handle_start))
        app.add_handler(CommandHandler("help", self.handlers.handle_help))
        app.add_handler(CommandHandler("status", self.handlers.handle_status))

        # Register general message handler
        app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handlers.handle_message)
        )

        self.application = app
        return app

    def run(self) -> None:
        """Start the Telegram bot using long polling."""
        if not self.application:
            self.build_application()

        logger.info("Starting Caspian Telegram bot polling...")
        self.application.run_polling()


def create_bot() -> CaspianTelegramBot:
    """Factory creating configured CaspianTelegramBot instance."""
    return CaspianTelegramBot()
