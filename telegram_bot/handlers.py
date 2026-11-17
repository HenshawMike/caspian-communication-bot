"""Telegram message and command handlers."""

from functools import wraps
from typing import Callable, Coroutine, Any
from telegram import Update
from telegram.ext import ContextTypes

from agent.config import settings
from agent.orchestrator import Orchestrator, orchestrator as default_orchestrator
from agent.skill_loader import skill_loader
from agent.tool_registry import registry as default_registry
from agent.logging_config import logger
from telegram_bot.keyboards import get_main_menu_keyboard


def authorized_only(func: Callable[..., Coroutine[Any, Any, None]]):
    """Decorator to ensure only the configured Telegram user can access the bot."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract update from method call (self, update, context) or function call (update, context)
        update: Any = None
        for arg in args:
            if hasattr(arg, "effective_user"):
                update = arg
                break
        if not update:
            update = kwargs.get("update")

        if not update or not getattr(update, "effective_user", None):
            return

        user = update.effective_user
        authorized_id = settings.telegram_authorized_user_id
        if authorized_id and str(user.id) != str(authorized_id):
            logger.warning(
                f"Unauthorized access attempt by user_id={user.id} (@{getattr(user, 'username', 'unknown')})"
            )
            if hasattr(update, "effective_message") and update.effective_message:
                await update.effective_message.reply_text(
                    "⛔ Unauthorized access. This is a private Project Caspian communications agent."
                )
            return

        return await func(*args, **kwargs)
    return wrapper


class TelegramHandlers:
    """Encapsulates bot command and message handling logic."""

    def __init__(self, orchestrator: Orchestrator = default_orchestrator):
        self.orchestrator = orchestrator

    @authorized_only
    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        user = update.effective_user
        first_name = user.first_name if user else "Researcher"
        welcome_text = (
            f"👋 Welcome {first_name} to **Project Caspian Agent**.\n\n"
            "I am your personal AI research communications agent.\n\n"
            "**Capabilities:**\n"
            "• Monitor Project Caspian repository for public research updates.\n"
            "• Collect and structure external AI intelligence.\n"
            "• Produce daily AI intelligence briefings.\n"
            "• Draft, verify, and publish content for X.\n\n"
            "Type a request or use the quick buttons below."
        )
        if update.effective_message:
            await update.effective_message.reply_text(
                welcome_text,
                parse_mode="Markdown",
                reply_markup=get_main_menu_keyboard(),
            )

    @authorized_only
    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        help_text = (
            "📖 **Project Caspian Agent Help**\n\n"
            "**Commands:**\n"
            "/start - Launch the agent and show main menu\n"
            "/status - Check agent operational health\n"
            "/help - Display this help guide\n\n"
            "**Example Requests:**\n"
            "• _Check Caspian repo for latest research_\n"
            "• _Give me the daily AI updates_\n"
            "• _Find recent papers on world models_\n"
            "• _Write an X post explaining our latest findings_\n"
        )
        if update.effective_message:
            await update.effective_message.reply_text(help_text, parse_mode="Markdown")

    @authorized_only
    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command."""
        skills = skill_loader.get_all_skills_metadata()
        tools = default_registry.get_tool_names()

        status_text = (
            "⚙️ **System Operational Status**\n\n"
            f"• **LLM Model:** `{settings.gemini_model}`\n"
            f"• **Database:** SQLite (WAL mode)\n"
            f"• **Registered Skills ({len(skills)}):**\n"
            + "\n".join([f"  - `{s.name}`" for s in skills])
            + f"\n• **Registered Tools ({len(tools)}):**\n"
            + "\n".join([f"  - `{t}`" for t in tools])
            + "\n\n🟢 System healthy and ready."
        )
        if update.effective_message:
            await update.effective_message.reply_text(status_text, parse_mode="Markdown")

    @authorized_only
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming natural language messages."""
        message = update.effective_message
        if not message or not message.text:
            return

        user_text = message.text.strip()
        user_id = str(update.effective_user.id) if update.effective_user else "unknown"

        # Shortcut for keyboard button "System status"
        if user_text.lower() == "system status":
            await self.handle_status(update, context)
            return

        # Forward request to orchestrator
        try:
            result = self.orchestrator.process_message(
                user_message=user_text,
                user_id=user_id,
            )

            if result["success"]:
                skill_info = result["skill"]
                reply = (
                    f"🎯 **Skill Activated:** {skill_info['name']}\n\n"
                    f"{result['message']}\n\n"
                    f"_Permissible tools:_ `{', '.join(skill_info['available_tools'])}`"
                )
            else:
                reply = result["message"]

            await message.reply_text(reply, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Error handling Telegram message: {e}")
            await message.reply_text(
                f"⚠️ An error occurred while processing your request: {str(e)}"
            )


handlers = TelegramHandlers()
