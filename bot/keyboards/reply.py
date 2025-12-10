from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def phone_number_button():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отправить номер телефона", request_contact=True)]],
        resize_keyboard=True
    )

def skip_button():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Пропускать")]],
        resize_keyboard=True
    )
