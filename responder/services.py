from pyrogram import Client
from pyrogram.enums import ChatType
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from django.utils import timezone

from responder import models as r_models
from responder.choices import VerificationStatusChoice
from django.db.models import Q
from environs import Env
from responder.models import BlackList
import json

env = Env()
env.read_env()

import re


def normalize_phone(phone: str | None) -> str | None:
    if not phone:
        return None

    phone = str(phone).strip()

    phone = re.sub(r"[^\d+]", "", phone)

    if phone.startswith("+"):
        phone = phone[1:]

    if phone.startswith("00"):
        phone = phone[2:]

    phone = re.sub(r"\D", "", phone)

    if len(phone) < 8:
        return None

    return phone


async def sync_group_users(client: Client, groups):
    print("=== SYNC STARTED ===")

    me = await client.get_me()
    print("SESSION USER:", me.id, me.username)

    group_map = {int(g.telegram_id): g for g in groups}

    async for dialog in client.get_dialogs():
        chat = dialog.chat

        if chat.id not in group_map:
            continue

        if chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
            continue

        g = group_map[chat.id]

        blacklist = None
        added_user_ids = set()

        async for member in client.get_chat_members(chat.id):
            user = member.user
            if not user or user.is_bot:
                continue

            if user.id in added_user_ids:
                continue

            user_phone = normalize_phone(user.phone_number)

            verification_qs = r_models.Verification.objects.filter(
                Q(chat_id=user.id) &
                ~Q(status=VerificationStatusChoice.ARCHIVE)
            )

            for verification in verification_qs:
                v_phone = normalize_phone(verification.phone_number)

                fields_present = []
                matched_fields = []

                if not verification.fullname:
                    fields_present.append("FULLNAME")
                    matched_fields.append("FULLNAME")

                if not verification.username:
                    fields_present.append("USERNAME")
                    matched_fields.append("USERNAME")

                if v_phone and user_phone:
                    fields_present.append("PHONE")
                    if v_phone == user_phone:
                        matched_fields.append("PHONE")

                if len(fields_present) >= 2 and len(matched_fields) == len(fields_present):

                    added_user_ids.add(user.id)

                    if blacklist is None:
                        blacklist = BlackList.objects.create(groups=g)

                    blacklist.verification.add(verification)

                    if not verification.is_blacklisted:
                        verification.is_blacklisted = True
                        verification.save(update_fields=["is_blacklisted"])

                    last_message = None
                    async for msg in client.get_chat_history(chat.id, limit=300):
                        if msg.from_user and msg.from_user.id == user.id:
                            last_message = msg
                            break

                    message_url = "—"
                    if last_message:
                        if chat.username:
                            message_url = f"https://t.me/{chat.username}/{last_message.id}"
                        else:
                            chat_id = str(chat.id).replace("-100", "")
                            message_url = f"https://t.me/c/{chat_id}/{last_message.id}"

                    checked_at_str = timezone.now().strftime("%d-%m-%Y %H:%M:%S")

                    text = (
                        "❗️ОБНАРУЖЕН В ЧЕРНОМ СПИСКЕ❗️\n\n"
                        f"🆔 Анкета ID: {verification.id}\n"
                        f"📌 Статус: {verification.get_status_display()}\n\n"
                        f"👤 ФИО: {verification.fullname or '—'}\n"
                        f"👤 Username: @{verification.username or '—'}\n"
                        f"📞 Телефон: {verification.phone_number or '—'}\n\n"
                        f"🚫 В черном списке: ДА\n"
                        f"🕒 Дата проверки: {checked_at_str}\n\n"
                        f"🔗 Источник:\n{message_url}"
                    )

                    await client.send_message(
                        chat_id=env.str("ADMIN"),
                        text=text,
                        disable_web_page_preview=True
                    )

                    photos = []
                    if verification.main_page_passport:
                        photos.append(InputMediaPhoto(verification.main_page_passport.path))
                    if verification.registration_page_passport:
                        photos.append(InputMediaPhoto(verification.registration_page_passport.path))

                    if photos:
                        await client.send_media_group(
                            chat_id=env.str("ADMIN"),
                            media=photos
                        )

                    break