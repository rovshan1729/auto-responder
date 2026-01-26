from aiogram import types
from django.db import models
from django.db.models import functions

from responder import models as r_models


class RegexpReplace(models.Func):
    function = 'regexp_replace'
    arity = 4


async def get_mask(text_list: str, credential: str | int, title: str = None):
    q_object = models.Q(telegram_id=credential)
    if isinstance(credential, str):
        q_object = models.Q(username=credential)

    is_blocked = r_models.TelegramUser.objects.filter(
        models.Q(is_blocked=True) & q_object
    ).exists()

    if not is_blocked:
        mask = r_models.Mask.objects.filter(
            text_list=text_list
        ).first()

        if title and mask and mask.groups and not 'ВСЕ ГРУППЫ' in mask.groups:
            groups = [name.lower() for name in mask.groups]

            if not any(group in title.lower() for group in groups):
                return None
        return mask
    return None


async def get_user_id(telegram_id: int) -> bool:
    return r_models.TelegramUser.objects.filter(
        telegram_id=telegram_id
    ).values_list('id', flat=True).first()


async def get_or_create_chat(telegram_id: int, defaults: dict):
    chat, created = await r_models.TelegramGroup.objects.aget_or_create(
        telegram_id=telegram_id,
        defaults=defaults
    )

    if created:
        return chat

    chat.status = defaults.get('status')
    chat.username = defaults.get('username')
    chat.title = defaults.get('title')
    chat.save(update_fields=['status', 'username', 'title'])

    return chat


async def get_command(command: str):
    return await r_models.TelegramCommand.objects.filter(
        command=command
    ).values('cleaned_content', 'file', 'file_id').afirst()


async def add_or_check_chat(chat_id: int):
    print(f"Worked add_or_check_chat: {chat_id}")
    data_obj = r_models.Data.get_solo()
    data_obj.channel_id = chat_id
    data_obj.save(update_fields=['channel_id'])
    print(f"Saved channel_id: {data_obj.channel_id}")


async def remove_chat(chat_id: int):
    data_obj = r_models.Data.get_solo()
    if data_obj.channel_id == chat_id:
        data_obj.channel_id = None
        data_obj.save(update_fields=['channel_id'])


async def get_data_model():
    return r_models.Data.get_solo()


def get_text(code):
    obj, created = r_models.StaticText.objects.get_or_create(
        code=code,
        defaults={"text": code}
    )
    return obj.text.replace("\\n", "\n")
