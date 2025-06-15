from aiogram import types
from aiogram.filters import Filter


class IsCommandFilter(Filter):
    def __init__(self):
        pass

    async def __call__(self, message: types.Message):
        if len(message.text.split(' ')) == 1 and message.text.startswith('/'):
            return True
        return False





