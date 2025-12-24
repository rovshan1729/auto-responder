from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def check_manager(chat_id):
    return {
        "inline_keyboard": [
            [
                {"text": "✅", "callback_data": f"accepted|{chat_id}"},
                {"text": "❌", "callback_data": f"closed|{chat_id}"},
            ]
        ]
    }
