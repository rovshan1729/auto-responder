from pyrogram import Client
from pyrogram.enums import ChatType

from responder import models as r_models
from responder.choices import VerificationStatusChoice


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

            telegram_id = str(user.id)
            group_telegram_ids.add(telegram_id)

            verification, created = r_models.Verification.objects.get_or_create(
                chat_id=user.id,
                defaults={
                    "is_blacklisted": True,
                    "status": VerificationStatusChoice.NoVERIFIED,
                }
            )

            if created:
                continue

            is_verified = (
                    verification.fullname and
                    verification.phone_number and
                    verification.status == VerificationStatusChoice.VERIFIED
            )

            verification.is_blacklisted = not is_verified
            verification.save(update_fields=["is_blacklisted"])

    return group_telegram_ids
