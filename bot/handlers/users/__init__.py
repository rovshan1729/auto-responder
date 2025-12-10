from aiogram import Router, F
from aiogram.enums import ChatType
from aiogram.filters import Command

from bot.filters import users, common
from bot.handlers.users.handle import *
from bot.states.states import RegistrationState


def prepare_router():
    router = Router()
    router.message.filter(F.chat.type == ChatType.PRIVATE)
    router.message.filter(common.IsSleepFilter())

    router.message.register(kyc_command_handler, Command("kyc"))
    router.message.register(get_phone_number_keyboard_handler, RegistrationState.phone_number)
    router.message.register(get_phone_number_addition_handler, RegistrationState.addition_number)
    router.message.register(command_handler, users.IsCommandFilter())
    router.message.register(respond_handler)

    return router
