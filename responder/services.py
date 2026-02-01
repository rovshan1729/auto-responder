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
    started_at = timezone.now()
    service_log = {
        "service": "sync_group_users",
        "started_at": started_at.strftime("%Y-%m-%d %H:%M:%S"),
        "ended_at": None,
        "checked_groups": []
    }
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

            user_phone = normalize_phone(user.phone_number)

            verification_qs = r_models.Verification.objects.filter(
                Q(chat_id=user.id) & ~Q(status=VerificationStatusChoice.ARCHIVE)
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

                print(f"{fields_present = }")
                print(f"{matched_fields = }")

                if len(fields_present) >= 2 and len(matched_fields) == len(fields_present):

                    last_message = None

                    async for msg in client.get_chat_history(chat.id, limit=300):
                        if msg.from_user and msg.from_user.id == user.id:
                            last_message = msg
                            break

                    message_url = " "
                    if last_message:
                        if chat.username:
                            message_url = f"https://t.me/{chat.username}/{last_message.id}"
                        else:
                            chat_id = str(chat.id).replace("-100", "")
                            message_url = f"https://t.me/c/{chat_id}/{last_message.id}"

                    checked_at_str = timezone.now().strftime("%d-%m-%Y %H:%M:%S")

                    blacklist_data = {
                        "verification_id": verification.id,
                        "chat_id": verification.chat_id,
                        "status": verification.status,
                        "fullname": verification.fullname,
                        "username": verification.username,
                        "phone_number": verification.phone_number,
                        "add_phone": verification.add_phone,
                        "email": verification.email,
                        "live_address": verification.live_address,
                        "geo": verification.geo,
                        "worked_platform": verification.worked_platform,
                        "experience": verification.experience,
                        "team_lead": verification.team_lead,
                        "recommend_user": verification.recommend_user,
                        "recommendation_user_contact": verification.recommendation_user_contact,
                        "additionally": verification.additionally,
                        "commentary": verification.commentary,
                        "matched_fields": matched_fields,
                        "source_message_url": message_url,
                        "checked_at": timezone.now().isoformat(),
                    }
                    BlackList.objects.create(data=blacklist_data)

                    text = (
                        "❗️ОБНАРУЖЕН В ЧЕРНОМ СПИСКЕ❗️\n\n"
                        f"🆔 Анкета ID: {verification.id}\n"
                        f"📌 Статус: {verification.get_status_display()}\n\n"

                        f"👤 ФИО: {verification.fullname or '—'}\n"
                        f"👤 Username: @{verification.username or '—'}\n"
                        f"📞 Телефон: {verification.phone_number or '—'}\n"
                        f"📞 Доп. телефон: {verification.add_phone or '—'}\n"
                        f"✉️ Email: {verification.email or '—'}\n\n"

                        f"🏠 Адрес проживания: {verification.live_address or '—'}\n"
                        f"🌍 Геолокация: {verification.geo or '—'}\n"
                        f"🌐 Рабочие платформы: {verification.worked_platform or '—'}\n\n"

                        f"💼 Опыт работы: {verification.experience or '—'}\n"
                        f"👨‍💼 Тимлид: {verification.team_lead or '—'}\n"
                        f"🤝 Рекомендовал: {verification.recommend_user or '—'}\n"
                        f"📇 Контакт рекомендателя: {verification.recommendation_user_contact or '—'}\n\n"

                        f"📝 Дополнительно: {verification.additionally or '—'}\n"
                        f"🗒 Комментарий администратора: {verification.commentary or '—'}\n\n"

                        f"🚫 В черном списке: {'ДА' if verification.is_blacklisted else 'НЕТ'}\n"
                        f"🕒 Дата последней проверки: {checked_at_str}\n\n"
                        f"\n🔗 Ссылка на источник:\n{message_url}"
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

    return group_telegram_ids
