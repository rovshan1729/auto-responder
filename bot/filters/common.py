from aiogram import types
from aiogram.filters import Filter

from bot import utils


class IsGroupFilter(Filter):
    def __init__(self):
        pass

    async def __call__(self, event: types.ChatMemberUpdated):
        if event.chat.type in ('group', 'supergroup'):
            return True
        return False


class IsChannelFilter(Filter):
    def __init__(self):
        pass

    async def __call__(self, event: types.ChatMemberUpdated):
        # print(f"chat_type: {event.chat.type}")
        if event.chat.type == 'channel':
            return True
        return False


class IsSleepFilter(Filter):
    def __init__(self):
        pass

    async def __call__(self, message: types.Message):
        data = await utils.get_data_model()
        if data.is_sleep:
            return False
        return True


class IsCommandFilter(Filter):
    def __init__(self):
        pass

    async def __call__(self, message: types.Message):
        if message and message.text and len(message.text.split(' ')) == 1 and message.text.startswith('/'):
            return True
        return False
