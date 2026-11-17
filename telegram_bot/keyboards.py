"""Telegram keyboard layouts and navigation buttons."""

from telegram import ReplyKeyboardMarkup, KeyboardButton


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Return standard reply keyboard for quick actions."""
    keyboard = [
        [
            KeyboardButton("Check Caspian"),
            KeyboardButton("Daily AI updates"),
        ],
        [
            KeyboardButton("Find AI research"),
            KeyboardButton("System status"),
        ],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
