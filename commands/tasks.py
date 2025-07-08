import time

from celery import shared_task

from responder.models import TelegramGroup
from bot.utils.methods import get_chat

@shared_task
def update_chats():
    chats = TelegramGroup.objects.all()
    for chat in chats:
        try:
            data = get_chat(chat.telegram_id)
        except Exception:
            time.sleep(1)
            continue

        if not data:
            continue

        title = data.get("result", {}).get("title", None)

        if not title:
            continue
        if chat.title != title:
            chat.title = title

    TelegramGroup.objects.bulk_update(chats, ["title"])


