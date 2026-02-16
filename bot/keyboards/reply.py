from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from responder.models import Country


def start_verification():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Приступить к верификации")],
            [KeyboardButton(text="Отменить")]
        ],
        resize_keyboard=True
    )


def phone_number_button():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Поделиться контактом", request_contact=True)]],
        resize_keyboard=True
    )


def skip_button():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Пропустить шаг")]],
        resize_keyboard=True
    )


def country_button():
    countries = Country.objects.all()
    keyboard = []
    row = []

    for idx, country in enumerate(countries, start=1):
        row.append(KeyboardButton(text=country.title))

        if idx % 2 == 0:
            keyboard.append(row)
            row = []

    if row:
        keyboard.append(row)

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )


def experience_button():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Менее года"), KeyboardButton(text="1 год")
            ],
            [
                KeyboardButton(text="2 года"), KeyboardButton(text="3 года")
            ],
            [
                KeyboardButton(text="5 лет"), KeyboardButton(text="Более 5 лет")
            ],
        ],
        resize_keyboard=True
    )


def verify_button():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Перепройти верификацию")]],
        resize_keyboard=True
    )


def next_broadcast_button():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Далее")]], resize_keyboard=True
    )
