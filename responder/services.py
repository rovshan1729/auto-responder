from .client import bot_app
from responder import models as r_models


def sync_group_users(groups):
    group_telegram_ids = set()

    if not bot_app.is_connected:
        bot_app.start()

    for group in groups:
        try:
            chat = bot_app.get_chat(group.telegram_id)
            for member in bot_app.get_chat_members(chat.id):
                user = member.user
                if not user or user.is_bot:
                    continue

                telegram_id = str(user.id)
                group_telegram_ids.add(telegram_id)

                verification, created = r_models.Verification.objects.get_or_create(
                    chat_id=telegram_id,
                    defaults={
                        "username": user.username,
                        "is_blacklisted": False,
                    }
                )

                if not created:
                    verification.username = user.username or verification.username
                    verification.is_blacklisted = bool(verification.username)
                    verification.save(update_fields=["username", "is_blacklisted"])

        except Exception as e:
            print(f"[Group {group.telegram_id}] error:", e)

    return group_telegram_ids
