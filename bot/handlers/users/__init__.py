from aiogram import Router, F
from aiogram.enums import ChatType

from bot.filters import users, common
from bot.handlers.users.handle import *



def prepare_router():
    router = Router()
    router.message.filter(F.chat.type == ChatType.PRIVATE)
    router.message.filter(common.IsSleepFilter())

    router.message.register(command_handler, users.IsCommandFilter())
    router.message.register(respond_handler)

    return router
