from aiogram import Router, F

from bot.filters.common import IsChannelFilter
from bot.handlers.channels.handle import bot_added_to_channel_as_admin


def prepare_router() -> Router:
    router = Router()
    router.my_chat_member.register(bot_added_to_channel_as_admin, IsChannelFilter())

    return router



