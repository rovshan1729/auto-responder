from pyrogram import Client
from pyrogram.enums import ChatType

from responder import models as r_models
from responder.choices import VerificationStatusChoice
from django.db.models import Q
from environs import Env

env = Env()
env.read_env()

async def sync_group_users(client: Client, groups):
    print("=== SYNC STARTED ===")

    group_telegram_ids = set()

    me = await client.get_me()
    print("SESSION USER:", me.id, me.username)

    group_ids = {int(g.telegram_id) for g in groups}

    async for dialog in client.get_dialogs():
        chat = dialog.chat

        if chat.id not in group_ids:
            continue

        if chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
            continue

        async for member in client.get_chat_members(chat.id):

            user = member.user
            if not user or user.is_bot:
                continue
            verification = r_models.Verification.objects.filter(
                chat_id=user.id,
                status=VerificationStatusChoice.VERIFIED
            ).exclude(
                fullname__isnull=True,
                phone_number__isnull=True
            )

            if verification.exists():
                print(f"SYNCED USER: {verification}")
                verification = verification.first()
                verification.is_blacklisted = False
                verification.save()

            else:
                if user.username:
                    username = user.username

                if user.phone_number:
                    phone_number = user.phone_number

                verification = r_models.Verification.objects.create(
                    chat_id=user.id,
                    username=username,
                    phone_number=phone_number,
                    status=VerificationStatusChoice.NoVERIFIED,
                    token=chat.title,
                    is_blacklisted=True
                )

                text = (
                    "🚫 Пользователь занесён в чёрный список\n\n"
                    f"ID: {user.id}\n"
                    f"Username: @{user.username if user.username else 'нет'}\n"
                    f"Телефон: {user.phone_number if user.phone_number else 'нет'}\n"
                    f"Группа: {chat.title}"
                )

                await client.send_message(
                    chat_id=env.str("ADMIN"),
                    text=text
                )
                verification.save()
                
            
    return group_telegram_ids
