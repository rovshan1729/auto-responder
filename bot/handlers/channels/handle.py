from aiogram import types
from aiogram.enums import ChatMemberStatus
from src.settings import ADMIN
from bot import utils


async def bot_added_to_channel_as_admin(event: types.ChatMemberUpdated):
    print(f"The function bot_added_to_channel_as_admin is called")
    if event.new_chat_member.status == ChatMemberStatus.ADMINISTRATOR:
        if str(event.from_user.id) == str(ADMIN):
            print("ADMINISTRATOR")
            await event.answer(
                f"Чат {event.chat.title} добавлен в базу данных"
            )
            return await utils.add_or_check_chat(event.chat.id)
        else:
            await event.answer(
                "Вы не являетесь администратором."
            )

    return await utils.remove_chat(event.chat.id)
