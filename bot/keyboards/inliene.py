from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from responder import models, choices


def check_manager(chat_id):
    return {
        "inline_keyboard": [
            [
                {"text": "✅", "callback_data": f"accepted|{chat_id}"},
                {"text": "❌", "callback_data": f"closed|{chat_id}"},
            ]
        ]
    }


def worker_choosing_action():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Начало работы", callback_data="stated_work")],
            [InlineKeyboardButton(text="Завершить работу", callback_data="finished_work")],
        ]
    )
    return keyboard


def finish_work_data_inline_button():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Отменить", callback_data="cancel")],
            [InlineKeyboardButton(text="Добавить диспут", callback_data="add_dispute")],
            [InlineKeyboardButton(text="Добавить проблему", callback_data="add_problem")],
        ]
    )
    return keyboard


def merchant_choosing_inline_button():
    merchants = models.Merchant.objects.all()

    keyboard = []
    for merchant in merchants:
        keyboard.append([InlineKeyboardButton(text=merchant.title, callback_data=f"merchant|{merchant.id}")])

    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    return markup


def get_dispute_count_inline_button():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Добавить еще", callback_data="add_more_dispute")],
            [InlineKeyboardButton(text="Далее", callback_data="add_more_text")]
        ]
    )
    return keyboard


def broadcast_group_keyboard(selected: list[str] | None = None):
    selected = selected or []

    buttons = []
    for g in choices.GroupChoice:
        mark = "✅ " if g.value in selected else ""
        buttons.append(
            InlineKeyboardButton(
                text=f"{mark}{g.label}",
                callback_data=f"broadcast_group|{g.value}"
            )
        )

    rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]

    rows.append([
        InlineKeyboardButton(
            text="Далее",
            callback_data="broadcast_group_done"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=rows)
