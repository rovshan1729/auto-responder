from aiogram import Router, F
from aiogram.enums import ChatType

from bot.filters import common
from bot.handlers.groups import handle

def prepare_router() -> Router:
    router = Router()
    router.message.filter(F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}))

    router.message.register(handle.command_handler, common.IsSleepFilter(), common.IsCommandFilter())
    router.message.register(handle.listen_message_handler)
    router.my_chat_member.register(handle.my_chat_member_update_handler, common.IsGroupFilter())

    return router
