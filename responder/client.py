# telegram_app/client.py
from pyrogram import Client
from django.conf import settings

bot_app = Client(
    name="telegram_session",
    api_id=settings.TG_API_ID,
    api_hash=settings.TG_API_HASH,
    bot_token=getattr(settings, "TG_BOT_TOKEN", None),
    workdir="sessions",
    in_memory=False
)
