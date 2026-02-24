from aiogram import types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove, InputMediaPhoto, FSInputFile
from django.db.models import Q
from pyrogram.filters import reply_keyboard

from responder.choices import VerificationStatusChoice, UserRole, DisputeStatus, GroupChoice
from asgiref.sync import sync_to_async
from django.core.files.base import ContentFile
from datetime import timedelta, datetime
from django.utils import timezone
from io import BytesIO
from django.utils.dateparse import parse_datetime
from django.db import transaction
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot import utils
from bot.keyboards import reply, inliene
from bot.states.states import RegistrationState, WorkerState, HeadReportState, BroadcastState, MaskState, MaskEditState, \
    MaskEditGroupsState
from responder import tasks, models
import os
from dotenv import load_dotenv

load_dotenv()


async def track_actions_handler(message: types.Message, message_data: dict):
    tasks.create_user_with_message.delay(message_data)


async def command_handler(message: types.Message):
    command = await utils.get_command(message.text.replace("/", ""))
    print(message.text)

    if not command:
        return

    photo = command.get("file_id") or command.get("file")

    if photo:
        input_photo = (
            photo if command.get("file_id") else types.FSInputFile(command["file"])
        )
        return await message.answer_photo(
            photo=input_photo,
            caption=command["cleaned_content"]
        )

    return await message.answer(command["cleaned_content"])


async def respond_handler(message: types.Message):
    credential = message.from_user.username or message.from_user.id

    text_list = utils.get_clean_sorted_text_list(message.text)
    mask = await utils.get_mask(text_list, credential)

    message_data = {
        "from_user": {
            "id": message.from_user.id,
            "username": message.from_user.username,
            "first_name": message.from_user.first_name,
            "last_name": message.from_user.last_name,
        },
        "text": message.text,
        "message_id": message.message_id,
    }

    await track_actions_handler(message, message_data)

    if mask:
        await message.reply(mask.cleaned_content)
        tasks.create_faq.delay(message.text, mask.id, telegram_id=message.from_user.id)
        tasks.mark_message.delay(
            message.message_id,
            message.from_user.id,
            mask=mask.cleaned_content
        )

    elif "?" in message.text:
        tasks.create_faq.delay(message.text, telegram_id=message.from_user.id)


async def kyc_command_handler(message: types.Message, state: FSMContext):
    await state.set_state(RegistrationState.start)
    await message.answer(
        utils.get_text("kyc_start_message"),
        reply_markup=reply.start_verification()
    )


async def get_user_start_verification_handler(message: types.Message, state: FSMContext):
    if message.text == "Приступить к верификации":
        await state.set_state(RegistrationState.phone_number)
        return await message.answer(
            utils.get_text("kyc_start_verification_prompt"),
            reply_markup=reply.phone_number_button()
        )
    elif message.text == "Отменить":
        await message.answer(
            utils.get_text("dont_start"), reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()


async def get_phone_number_keyboard_handler(message: types.Message, state: FSMContext):
    if not message.contact:
        return await message.answer(
            utils.get_text("kyc_start_verification_prompt"),
            reply_markup=reply.phone_number_button()
        )

    phone_number = message.contact.phone_number
    await state.update_data(phone_number=phone_number)

    try:
        verification = await sync_to_async(models.Verification.objects.create)(
            chat_id=str(message.from_user.id),
            phone_number=phone_number,
            status=VerificationStatusChoice.NO_PASSED
        )
    except Exception as e:
        utils.send_text(2131715946, text=f"Verification create error: {e}")
        raise

    await state.update_data(verification_id=verification.id)
    await state.set_state(RegistrationState.addition_number)

    await message.answer(
        utils.get_text("phone_number_addition_handler"),
        reply_markup=reply.skip_button()
    )


async def get_phone_number_addition_handler(message: types.Message, state: FSMContext):
    text = message.text.strip()

    if text == "Пропустить шаг":
        await state.update_data(add_phone=None)
        await state.set_state(RegistrationState.email)
        return await message.answer(
            utils.get_text("additional_phone_skip"),
            reply_markup=ReplyKeyboardRemove()
        )

    phone = message.contact.phone_number if message.contact else None
    data = await state.get_data()

    if not phone or not utils.is_valid_phone(phone) or phone == data.get("phone_number"):
        return await message.answer(
            utils.get_text("additional_phone_invalid"),
            reply_markup=ReplyKeyboardRemove()
        )

    await state.update_data(add_phone=phone)
    await state.set_state(RegistrationState.email)
    await message.answer(
        utils.get_text("additional_phone_accepted"),
        reply_markup=ReplyKeyboardRemove()
    )


async def get_email_handler(message: types.Message, state: FSMContext):
    email = message.text.strip()

    if not utils.is_valid_email(email):
        return await message.answer(utils.get_text("email_invalid"))

    await state.update_data(email=email)
    await state.set_state(RegistrationState.token)
    await message.answer(utils.get_text("email_accepted"))


async def get_token_handler(message: types.Message, state: FSMContext):
    token = message.text.strip()

    group = models.TelegramGroup.objects.filter(title__contains=token).first()

    if not group:
        return await message.answer(utils.get_text("token_invalid"))

    await state.update_data(token=group.title)
    await state.set_state(RegistrationState.team_lead)

    await message.answer(utils.get_text("token_request"), reply_markup=reply.skip_button())


async def get_team_lead_handler(message: types.Message, state: FSMContext):
    if message.text == "Пропустить шаг":
        await state.update_data(team_lead=None)
        await state.set_state(RegistrationState.recommend_user)
        return await message.answer(utils.get_text("team_lead_skip"))

    await state.update_data(team_lead=message.text)
    await state.set_state(RegistrationState.recommend_user)
    await message.answer(utils.get_text("team_lead_skip"))


async def get_recommend_user_handler(message: types.Message, state: FSMContext):
    await state.update_data(recommend_user=message.text)
    await state.set_state(RegistrationState.country)
    await message.answer(utils.get_text("recommend_user_request"), reply_markup=reply.country_button())


async def get_country_handler(message: types.Message, state: FSMContext):
    country = models.Country.objects.filter(title__icontains=message.text).first()

    if not country:
        return await message.answer(utils.get_text("country_not_found"), reply_markup=reply.country_button())

    await state.update_data(country=country.pk)
    await state.set_state(RegistrationState.fullname)

    await message.answer(utils.get_text("country_accepted"), reply_markup=ReplyKeyboardRemove())


async def get_user_fullname_handler(message: types.Message, state: FSMContext):
    parts = message.text.split()

    if len(parts) < 2:
        return await message.answer(utils.get_text("fullname_invalid"))

    await state.update_data(fullname=message.text)
    await state.set_state(RegistrationState.live_address)

    await message.answer(
        utils.get_text("fullname_request")
    )


async def get_user_current_live_address_handler(message: types.Message, state: FSMContext):
    parts = message.text.split(" ")

    if len(parts) < 2:
        return await message.answer(utils.get_text("address_invalid"))

    await state.update_data(live_address=message.text)
    await state.set_state(RegistrationState.main_page_passport)

    await message.answer(utils.get_text("address_request"))


async def get_user_main_page_passport_handler(message: types.Message, state: FSMContext):
    if not message.photo:
        return await message.answer(
            utils.get_text("passport_main_page_error")
        )

    await state.update_data(
        main_page_passport_id=message.photo[-1].file_id
    )

    await state.set_state(RegistrationState.registration_page_passport)
    await message.answer(
        utils.get_text("passport_main_page_request")
    )


async def get_user_registration_page_passport_handler(message: types.Message, state: FSMContext):
    if not message.photo:
        return await message.answer(
            utils.get_text("passport_registration_page_error")
        )

    await state.update_data(
        registration_page_passport_id=message.photo[-1].file_id
    )

    await state.set_state(RegistrationState.additional_information_passport)
    await message.answer(
        utils.get_text("passport_additional_page_request"), reply_markup=reply.skip_button()
    )


async def get_user_additional_information_passport_handler(message: types.Message, state: FSMContext):
    if message.text == "Пропустить шаг":
        await state.update_data(
            additional_information_passport_id=None
        )
    else:
        if not message.photo:
            return await message.answer(
                utils.get_text("passport_additional_page_error")
            )

        await state.update_data(
            additional_information_passport_id=message.photo[-1].file_id
        )

    await state.set_state(RegistrationState.round_video)
    await message.answer(
        utils.get_text("request_for_video"),
        reply_markup=types.ReplyKeyboardRemove()
    )


async def get_user_round_video_handler(message, state):
    if not message.video_note:
        return await message.answer(
            utils.get_text("round_video_invalid")
        )

    await state.update_data(
        round_video_id=message.video_note.file_id
    )

    await state.set_state(RegistrationState.geo)
    await message.answer(
        utils.get_text("round_video_request")
    )


async def get_user_geo_handler(message, state):
    await state.update_data(geo=message.text)
    await state.set_state(RegistrationState.experience)

    await message.answer(
        utils.get_text("geo_request"),
        reply_markup=reply.experience_button()
    )


async def get_user_experience_handler(message, state):
    valid = ["Менее года", "1 год", "2 года", "3 года", "5 лет", "Более 5 лет"]

    if message.text not in valid:
        return await message.answer(utils.get_text("experience_invalid"))

    await state.update_data(experience=message.text)
    await state.set_state(RegistrationState.worked_platform)

    await message.answer(
        utils.get_text("experience_request"),
        reply_markup=ReplyKeyboardRemove()
    )


async def get_user_worked_platform_handler(message, state):
    await state.update_data(worked_platform=message.text)
    await state.set_state(RegistrationState.recommendation_user_contact)

    await message.answer(utils.get_text("worked_platform_request"))


async def _save_file_from_telegram(bot, file_id, filename):
    file = await bot.get_file(file_id)
    buffer = BytesIO()
    await bot.download_file(file.file_path, destination=buffer)
    buffer.seek(0)
    return ContentFile(buffer.read(), name=filename)


async def get_user_recommendation_user_contact_handler(message: types.Message, state: FSMContext):
    await state.update_data(recommendation_user_contact=message.text)
    await message.answer(
        utils.get_text("verification_success"),
    )
    try:
        data = await state.get_data()

        verification = await sync_to_async(models.Verification.objects.get)(
            pk=data["verification_id"]
        )
        phone_number = data.get("phone_number")
        add_phone = data.get("add_phone")
        email = data.get("email")
        token = data.get("token")
        team_lead = data.get("team_lead")
        recommend_user = data.get("recommend_user")
        country_id = data.get("country")
        fullname = data.get("fullname")
        live_address = data.get("live_address")
        geo = data.get("geo")
        experience = data.get("experience")
        worked_platform = data.get("worked_platform")
        recommendation_user_contact = data.get("recommendation_user_contact")
        status = VerificationStatusChoice.WAITING

        if data.get("main_page_passport_id"):
            verification.main_page_passport = await _save_file_from_telegram(
                message.bot,
                data["main_page_passport_id"],
                f"{verification.pk}_main_passport.jpg"
            )

        if data.get("registration_page_passport_id"):
            verification.registration_page_passport = await _save_file_from_telegram(
                message.bot,
                data["registration_page_passport_id"],
                f"{verification.pk}_registration_page_passport.jpg"
            )

        if data.get("additional_information_passport_id"):
            verification.additional_information_passport = await _save_file_from_telegram(
                message.bot,
                data["additional_information_passport_id"],
                f"{verification.pk}_additional_information_passport.jpg"
            )

        if data.get("round_video_id"):
            verification.round_video = await _save_file_from_telegram(
                message.bot,
                data["round_video_id"],
                f"{verification.pk}_round_video.mp4"
            )
        text = (
            "🛂 <b>Новая заявка на верификацию</b>\n\n"
            f"👤 <b>ФИО:</b> {fullname}\n"
            f"📞 <b>Основной телефон:</b> {phone_number}\n"
            f"📱 <b>Доп. телефон:</b> {add_phone}\n"
            f"📧 <b>Email:</b> {email}\n"
            f"🌍 <b>Страна ID:</b> {country_id}\n"
            f"🏠 <b>Адрес проживания:</b> {live_address}\n"
            f"📍 <b>Геолокация:</b> {geo}\n\n"
            f"💼 <b>Опыт работы:</b> {experience}\n"
            f"🧑‍💻 <b>Платформы:</b> {worked_platform}\n\n"
            f"👨‍💼 <b>Team Lead:</b> {team_lead}\n"
            f"⭐ <b>Рекомендовал:</b> {recommend_user}\n"
            f"📞 <b>Контакт рекомендателя:</b> {recommendation_user_contact}\n\n"
            f"📌 <b>Статус:</b> {status}"
        )
        admin_chat_id = models.Profile.objects.filter(
            role=UserRole.VERIFICATOR
        ).select_related("user").values_list(
            "user__telegram_id", flat=True
        ).first()
        multi_files = []
        main_page_passport_id = data["main_page_passport_id"]
        multi_files.append(main_page_passport_id)
        registration_page_passport_id = data["registration_page_passport_id"]
        multi_files.append(registration_page_passport_id)
        additional_information_passport_id = data.get("additional_information_passport_id")
        if additional_information_passport_id:
            multi_files.append(additional_information_passport_id)
        round_video_id = data["round_video_id"]
        utils.send_file(admin_chat_id, file_type="video", file_id=round_video_id)

        utils.send_multi_file_by_file_id(admin_chat_id, file_type="photo",
                                         file_ids=multi_files)
        utils.send_text(admin_chat_id, text=text, reply_markup=inliene.check_manager(verification.pk))
        verification.username = message.chat.username
        verification.phone_number = phone_number
        verification.add_phone = add_phone
        verification.email = email
        verification.token = token
        verification.team_lead = team_lead
        verification.recommend_user = recommend_user
        verification.recommendation_user_contact = recommendation_user_contact
        verification.status = status
        verification.country_id = country_id
        verification.fullname = fullname
        verification.live_address = live_address
        verification.geo = geo
        verification.experience = experience
        verification.worked_platform = worked_platform

        await sync_to_async(verification.save)()

    except Exception as e:
        print("error:", e)

    return await state.clear()


async def accept_handler(callback: types.CallbackQuery, state: FSMContext):
    verification_id = callback.data.split("|")[1]

    user = models.Verification.objects.filter(pk=verification_id).first()

    if not user:
        return

    base_time = user.updated_at or timezone.now()
    user.expires_at = base_time + timedelta(days=90)
    user.status = VerificationStatusChoice.VERIFIED
    user.save(update_fields=["expires_at", "status"])

    username = user.fullname or f"@{callback.from_user.username}"
    expired_at = user.expires_at.strftime("%d.%m.%Y %H:%M")
    token = user.token
    group = models.TelegramGroup.objects.filter(title__contains=token).first()
    await callback.message.edit_reply_markup(
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅",
                        callback_data="verified_done"
                    )
                ]
            ]
        )
    )
    user_text = (
        "✅ <b>Верификация подтверждена</b>\n\n"
        f"👤 Пользователь: {username}\n"
        f"⏳ Срок действия: <b>{expired_at}</b>\n\n"
        "Теперь вы можете пользоваться сервисом без ограничений."
    )
    utils.send_text(user.chat_id, user_text)
    group_text = (
        "🟢 <b>Верификация подтверждена</b>\n\n"
        f"👤 Пользователь: {username}\n"
        f"📞 Телефон: {user.phone_number}\n"
        f"🌍 Страна: {user.country}\n"
        f"⏳ Действует до: <b>{expired_at}</b>"
    )
    utils.send_text(group.telegram_id, group_text)


async def closed_handler(callback: types.CallbackQuery, state: FSMContext):
    verification_id = int(callback.data.split("|")[1])

    user = models.Verification.objects.filter(pk=verification_id).first()
    if not user:
        return

    user.status = VerificationStatusChoice.NoVERIFIED
    user.save(update_fields=["expires_at", "status"])
    token = user.token
    await callback.message.edit_reply_markup(
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="❌",
                        callback_data="verified_close"
                    )
                ]
            ]
        )
    )
    keyboard = {
        "keyboard": [
            [{"text": "Приступить к верификации"}]
        ],
        "resize_keyboard": True
    }

    username = user.fullname or f"@{callback.from_user.username}"
    user_text = (
        "❌ <b>Верификация не подтверждена</b>\n\n"
        "К сожалению, ваша верификация была отклонена.\n"
        "Вы можете начать процесс заново."
    )

    utils.send_text(
        user.chat_id,
        user_text,
        reply_markup=keyboard
    )

    group_text = (
        "🔴 <b>Верификация отклонена</b>\n\n"
        f"👤 Пользователь: {username}\n"
        f"📞 Телефон: {user.phone_number}\n"
        f"🌍 Страна: {user.country}\n"
        f"📌 Статус: <b>Отклонена</b>"
    )

    group = models.TelegramGroup.objects.filter(title__contains=token).first()

    utils.send_text(group.telegram_id, group_text)

    await state.clear()


async def start_verification_after_close_handler(message: types.Message, state: FSMContext):
    await state.set_state(RegistrationState.phone_number)
    return await message.answer(
        utils.get_text("kyc_start_verification_prompt"),
        reply_markup=reply.phone_number_button()
    )


async def support_worker_handler(message: types.Message, state: FSMContext):
    profile = models.Profile.objects.filter(
        user__telegram_id=message.from_user.id,
        role=UserRole.SUPPORT
    ).first()

    if not profile:
        await message.answer("У вас нет доступа к этой команде.")
        return

    await state.clear()
    await message.answer(
        utils.get_text("worker_start_message"),
        reply_markup=inliene.worker_choosing_action()
    )


async def worker_start_work_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    chat_id = callback.from_user.id
    profile = models.Profile.objects.filter(user__telegram_id=chat_id, role__in=[UserRole.SUPPORT, UserRole.ADMIN])
    await callback.message.delete()

    if profile.exists():
        profile = profile.first()
        worker_data = models.WorkerData.objects.filter(profile=profile)
        if worker_data.exists() and worker_data.first().finish_work_time is not None:
            models.WorkerData.objects.create(profile=profile, start_work_time=timezone.now().isoformat())
            await callback.message.answer(utils.get_text("worker_start_work_message"))
            head_profile = models.Profile.objects.filter(role=UserRole.HEAD_SUPPORT).first()
            text = f"Саппорт @{callback.from_user.username} начал работу в {timezone.now().isoformat()}\n"
            utils.send_text(head_profile.user.telegram_id, text)

        elif not worker_data.exists():
            models.WorkerData.objects.create(profile=profile, start_work_time=timezone.now().isoformat())
            await callback.message.answer(utils.get_text("worker_start_work_message"))
            head_profile = models.Profile.objects.filter(role=UserRole.HEAD_SUPPORT).first()
            text = f"Саппорт @{callback.from_user.username} начал работу в {timezone.now().isoformat()}\n"
            utils.send_text(head_profile.user.telegram_id, text)

        else:
            await callback.message.answer(utils.get_text("worker_doesnt_finish_work"))
    else:
        await callback.message.answer(utils.get_text("default_user"))


async def worker_finish_work_handler(callback: types.CallbackQuery, state: FSMContext):
    profile = models.Profile.objects.filter(
        user__telegram_id=callback.from_user.id,
        role__in=[UserRole.SUPPORT, UserRole.ADMIN]
    ).first()
    if not profile:
        await callback.answer("Нет доступа", show_alert=True)
        return

    chat_id = callback.from_user.id
    work_data = models.WorkerData.objects.filter(profile__user__telegram_id=chat_id, finish_work_time__isnull=True)
    await callback.message.delete()
    if work_data.exists():
        await callback.message.answer(utils.get_text("choice_finish_work"),
                                      reply_markup=inliene.finish_work_data_inline_button())
        await state.set_state(WorkerState.finish_work)
    else:
        await callback.message.answer(utils.get_text("worker_doesnt_finish_work"))


async def cancel_finish_work_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    await callback.message.answer(utils.get_text("cancel_finish_work"))
    await state.clear()


async def dispute_add_handler(callback: types.CallbackQuery, state: FSMContext):
    profile = models.Profile.objects.filter(
        user__telegram_id=callback.from_user.id,
        role__in=[UserRole.SUPPORT, UserRole.ADMIN]
    ).first()
    if not profile:
        await callback.answer("Нет доступа", show_alert=True)
        return

    await callback.message.delete()
    merchants = models.Merchant.objects.all()
    if merchants.count() > 0:
        await callback.message.answer(utils.get_text("choice_merchant"),
                                      reply_markup=inliene.merchant_choosing_inline_button(merchants))
        await state.set_state(WorkerState.merchant)
    else:
        await callback.message.answer(utils.get_text("no_merchant"), reply_markup=inliene.worker_choosing_action())
        await state.clear()


async def get_merchant_handler(callback: types.CallbackQuery, state: FSMContext):
    profile = models.Profile.objects.filter(
        user__telegram_id=callback.from_user.id,
        role__in=[UserRole.SUPPORT, UserRole.ADMIN]
    ).first()
    if not profile:
        await callback.answer("Нет доступа", show_alert=True)
        return

    try:
        await callback.message.delete()
    except:
        pass

    merchant_id = int(callback.data.split("|")[1])
    await callback.message.answer(utils.get_text("get_merchant"))
    await state.update_data({"current_merchant_id": merchant_id})
    await state.set_state(WorkerState.new_dispute_count)


async def get_new_dispute_handler(message: types.Message, state: FSMContext):
    profile = models.Profile.objects.filter(
        user__telegram_id=message.from_user.id,
        role__in=[UserRole.SUPPORT, UserRole.ADMIN]
    ).first()

    if not profile:
        await message.answer("Нет доступа", show_alert=True)
        return

    text = message.text.strip()
    if not text.isdigit():
        await message.answer("Просто введите число. Например: 3")
        return

    count = int(text)

    data = await state.get_data()
    merchant_id = data.get("current_merchant_id")
    if not merchant_id:
        await message.answer("Продавец не выбран. Пожалуйста, попробуйте еще раз.")
        return

    disputes = data.get("disputes", [])

    merchant_data = next((d for d in disputes if d["merchant_id"] == merchant_id), None)

    if merchant_data:
        merchant_data["new_dispute_count"] = count
    else:
        disputes.append({
            "merchant_id": merchant_id,
            "new_dispute_count": count,
            "resolved_dispute_count": 0
        })

    await state.update_data({"disputes": disputes})
    await message.answer(utils.get_text("get_new_dispute_count"))
    await state.set_state(WorkerState.resolved_dispute_count)


async def get_resolved_dispute_count_handler(message: types.Message, state: FSMContext):
    profile = models.Profile.objects.filter(
        user__telegram_id=message.from_user.id,
        role__in=[UserRole.SUPPORT, UserRole.ADMIN]
    ).first()
    if not profile:
        await message.answer("Нет доступа", show_alert=True)
        return

    text = message.text.strip()

    if not text.isdigit():
        await message.answer("Просто введите число. Например: 3")
        return

    data = await state.get_data()
    merchant_id = data.get("current_merchant_id")

    if not merchant_id:
        await message.answer("Продавец не выбран. Пожалуйста, попробуйте еще раз.")
        return

    resolved_count = int(text)
    disputes = data.get("disputes", [])

    merchant_data = next((d for d in disputes if d["merchant_id"] == merchant_id), None)

    new_count = merchant_data.get("new_dispute_count", 0) if merchant_data else 0

    if resolved_count > new_count:
        await message.answer(
            f"Решенных диспутов не может быть больше новых.\n"
            f"Новые: {new_count}\n"
            f"Введите число от 0 до {new_count}."
        )
        await state.set_state(WorkerState.resolved_dispute_count)
        return

    if merchant_data:
        merchant_data["resolved_dispute_count"] = resolved_count
    else:
        disputes.append({
            "merchant_id": merchant_id,
            "new_dispute_count": 0,
            "resolved_dispute_count": resolved_count
        })

    await state.update_data({"disputes": disputes})
    await message.answer(utils.get_text("get_dispute_count"), reply_markup=inliene.get_dispute_count_inline_button())
    await state.set_state(WorkerState.cycle)


async def get_add_more_dispute_handler(callback: types.CallbackQuery, state: FSMContext):
    try:
        await callback.message.delete()
    except:
        pass

    if callback.data == "add_more_dispute":
        merchants = models.Merchant.objects.all()
        await callback.message.answer(utils.get_text("choice_merchant"),
                                      reply_markup=inliene.merchant_choosing_inline_button(merchants))
        await state.set_state(WorkerState.merchant)

    elif callback.data == "add_more_text":
        await callback.message.answer(utils.get_text("get_problem_info"))
        await state.set_state(WorkerState.get_problem)


async def get_problem_text_handler(message: types.Message, state: FSMContext):
    profile = models.Profile.objects.filter(
        user__telegram_id=message.from_user.id,
        role__in=[UserRole.SUPPORT, UserRole.ADMIN]
    ).first()

    if not profile:
        await message.answer("Нет доступа")
        return

    chat_id = message.from_user.id
    problem_text_input = message.text.strip()

    data = await state.get_data()
    disputes = data.get("disputes", [])

    work_data = models.WorkerData.objects.filter(
        profile__user__telegram_id=chat_id,
        finish_work_time__isnull=True
    ).select_related("profile__user").first()

    if not work_data:
        await message.answer(utils.get_text("no_work"))
        return

    report, _ = models.WorkerShiftReport.objects.get_or_create(
        worker_data=work_data
    )

    report.is_submitted = True
    report.submitted_at = timezone.now()
    report.save(update_fields=["comment", "is_submitted", "submitted_at"])
    for d in disputes:
        merchant_id = int(d.get("merchant_id"))
        new_count = int(d.get("new_dispute_count"))
        resolved_count = int(d.get("resolved_dispute_count"))
        if not merchant_id or new_count is None or resolved_count is None:
            continue
        unresolved_count = new_count - resolved_count
        models.WorkerMerchantStat.objects.create(
            report=report,
            merchant_id=merchant_id,
            new_count=new_count,
            resolved_count=resolved_count,
            unresolved_count=unresolved_count
        )
    work_data.finish_work_time = timezone.now()
    work_data.save(update_fields=["finish_work_time"])

    head_profile = models.Profile.objects.filter(
        role=UserRole.HEAD_SUPPORT
    ).select_related("user").first()
    if head_profile:
        username = message.from_user.username or message.from_user.full_name

        start_time_str = timezone.localtime(
            work_data.start_work_time
        ).strftime("%d.%m.%Y %H:%M:%S")

        end_time_str = timezone.localtime(
            work_data.finish_work_time
        ).strftime("%d.%m.%Y %H:%M:%S")

        db_disputes = report.merchant_stats.select_related("merchant").all()

        grouped: dict[str, dict[str, int]] = {}

        for item in db_disputes:
            title = item.merchant.title

            if title not in grouped:
                grouped[title] = {
                    "new": 0,
                    "resolved": 0,
                    "unresolved": 0,
                }

            grouped[title]["new"] += item.new_count or 0
            grouped[title]["resolved"] += item.resolved_count or 0

        for title in grouped:
            grouped[title]["unresolved"] = max(
                grouped[title]["new"] - grouped[title]["resolved"],
                0
            )

        lines = []

        for merchant_title in sorted(grouped.keys()):
            stats = grouped[merchant_title]

            lines.append(
                f"{merchant_title} | решенные {stats['resolved']} | не решенные {stats['unresolved']} | новые {stats['new']}"
            )

        disputes_block = "\n".join(lines) if lines else "Нет диспутов"
        models.Problem.objects.create(profile=profile, text=problem_text_input)
        head_text = (
            "Отчет о смене:\n"
            f"Саппорт: @{username}\n"
            f"Дата начала: {start_time_str}\n"
            f"Дата завершения: {end_time_str}\n\n"
            "Диспуты:\n"
            f"{disputes_block}\n\n"
            "Проблемы:\n"
            f"{problem_text_input}"
        )

        utils.send_text(
            head_profile.user.telegram_id,
            head_text
        )

    await message.answer(utils.get_text("the_shift_assigned"))
    await state.clear()


async def get_add_problem_support_handler(callback: types.CallbackQuery, state: FSMContext):
    profile = models.Profile.objects.filter(
        user__telegram_id=callback.from_user.id,
        role__in=[UserRole.SUPPORT, UserRole.ADMIN]
    ).first()
    await callback.message.delete()
    if not profile:
        await callback.answer("Нет доступа", show_alert=True)
        return

    await callback.message.answer(utils.get_text("send_text_add_problem"))
    await state.set_state(WorkerState.add_problem)


async def get_add_problem_text_support_handler(message: types.Message, state: FSMContext):
    problem_text = message.text.strip()

    profile = models.Profile.objects.filter(user__telegram_id=message.from_user.id).first()
    if not profile:
        await message.answer(utils.get_text("none_profile"))
        return

    models.Problem.objects.create(profile=profile, text=problem_text)

    head_profile = models.Profile.objects.filter(role=UserRole.HEAD_SUPPORT).first()
    if head_profile:
        username = message.from_user.username or message.from_user.full_name

        text = (
            "Проблемы:\n"
            f"@{username} - {problem_text}"
        )

        utils.send_text(head_profile.user.telegram_id, text)

    await message.answer(utils.get_text("get_problem_text_support"))
    await state.clear()


async def head_report_command(message: types.Message, state: FSMContext):
    profile = models.Profile.objects.filter(
        user__telegram_id=message.from_user.id,
        role__in=[UserRole.HEAD_SUPPORT, UserRole.ADMIN]
    ).first()
    if not profile:
        await message.answer(utils.get_text("access_denied"))
        return

    await state.clear()
    await message.answer("Введите дату ОТ (формат: ДД.ММ.ГГГГ)\nПример: 25.01.2026")
    await state.set_state(HeadReportState.date_from)


async def head_report_date_from_handler(message: types.Message, state: FSMContext):
    date_from = utils.parse_date_ru(message.text)

    if not date_from:
        await message.answer("Неверный формат даты. Пример: 25.01.2026")
        return

    await state.update_data({"date_from": str(date_from)})
    await message.answer("Введите дату ДО (формат: ДД.ММ.ГГГГ)\nПример: 26.01.2026")
    await state.set_state(HeadReportState.date_to)


async def head_report_date_to_handler(message: types.Message, state: FSMContext):
    date_to = utils.parse_date_ru(message.text)

    if not date_to:
        await message.answer("Неверный формат даты. Пример: 26.01.2026")
        return

    data = await state.get_data()
    date_from_str = data.get("date_from")

    if not date_from_str:
        await message.answer("Дата ОТ не найдена. Введите /report заново.")
        await state.clear()
        return

    date_from = datetime.strptime(date_from_str, "%Y-%m-%d").date()

    if date_to < date_from:
        await message.answer("Дата ДО не может быть меньше даты ОТ.")
        return

    dt_from = timezone.make_aware(datetime.combine(date_from, datetime.min.time()))
    dt_to = timezone.make_aware(datetime.combine(date_to, datetime.max.time()))

    report_ids = models.WorkerShiftReport.objects.filter(
        is_submitted=True,
        submitted_at__gte=dt_from,
        submitted_at__lte=dt_to
    ).values_list("id", flat=True)
    disputes = models.WorkerMerchantStat.objects.filter(
        report_id__in=report_ids
    ).select_related("merchant")

    if not disputes.exists():
        await message.answer(utils.get_text("none_dispute"))
        await state.clear()
        return

    grouped = {}
    total = {"resolved": 0, "new": 0, "unresolved": 0}

    for d in disputes:
        title = d.merchant.title

        if title not in grouped:
            grouped[title] = {"resolved": 0, "new": 0, "unresolved": 0}

        new_count = d.new_count or 0
        resolved_count = d.resolved_count or 0
        unresolved_count = d.unresolved_count or 0

        grouped[title]["new"] += new_count
        grouped[title]["resolved"] += resolved_count
        grouped[title]["unresolved"] += unresolved_count

        total["new"] += new_count
        total["resolved"] += resolved_count
        total["unresolved"] += unresolved_count

    lines = []
    lines.append("Отчет по диспутам")
    lines.append(f"Период: {date_from.strftime('%d.%m.%Y')} - {date_to.strftime('%d.%m.%Y')}")
    lines.append("")
    lines.append("По мерчантам:")

    for merchant_title in sorted(grouped.keys()):
        r = grouped[merchant_title]["resolved"]
        n = grouped[merchant_title]["new"]
        u = grouped[merchant_title]["unresolved"]

        lines.append(f"{merchant_title} | решённые {r} | нерешённые {u} | новые {n}")

    lines.append("")
    lines.append(
        f"ИТОГО: решённые {total['resolved']} | нерешённые {total['unresolved']} | новые {total['new']} "
    )

    await message.answer("\n".join(lines))
    await state.clear()


async def broadcast_command_handler(message: types.Message, state: FSMContext):
    profile = models.Profile.objects.filter(
        user__telegram_id=message.from_user.id,
        role__in=[UserRole.SUPPORT, UserRole.HEAD_SUPPORT, UserRole.ADMIN]
    ).first()

    if not profile:
        await message.answer(utils.get_text("access_denied"))
        return

    await state.clear()
    await message.answer(utils.get_text("show_title"))
    await state.set_state(BroadcastState.title)


async def broadcast_title_handler(message: types.Message, state: FSMContext):
    profile = models.Profile.objects.filter(
        user__telegram_id=message.from_user.id,
        role__in=[UserRole.SUPPORT, UserRole.HEAD_SUPPORT, UserRole.ADMIN]
    ).first()

    if not profile:
        await message.answer(utils.get_text("access_denied"))
        return

    title = message.text.strip()

    await state.update_data({"title": title})
    await message.answer(utils.get_text("show_template_id"), reply_markup=reply.skip_button())
    await state.set_state(BroadcastState.template_id)


from broadcast.models import Broadcast, BroadcastTemplate, BroadcastButton, Media


async def broadcast_template_id_handler(message: types.Message, state: FSMContext):
    template_id = message.text.strip()

    if template_id == "Пропустить шаг":
        await state.update_data({"template_id": None})
        await message.answer(utils.get_text("show_content"), reply_markup=ReplyKeyboardRemove())
        await state.set_state(BroadcastState.content)
        return

    profile = models.Profile.objects.filter(
        user__telegram_id=message.from_user.id,
        role__in=[UserRole.SUPPORT, UserRole.HEAD_SUPPORT, UserRole.ADMIN]
    ).first()

    if not profile:
        await message.answer(utils.get_text("access_denied"))
        return

    if template_id.isdigit():
        template = BroadcastTemplate.objects.filter(pk=template_id).first()
        if not template:
            await message.answer(utils.get_text("show_template_id"))
            await state.set_state(BroadcastState.template_id)
            return

        await state.update_data({"template_id": int(template_id)})

        await message.answer(utils.get_text("show_content"), reply_markup=ReplyKeyboardRemove())
        await state.set_state(BroadcastState.content)
        return

    await message.answer(utils.get_text("show_template_id"))
    await state.set_state(BroadcastState.template_id)


async def broadcast_content_handler(message: types.Message, state: FSMContext):
    profile = models.Profile.objects.filter(
        user__telegram_id=message.from_user.id,
        role__in=[UserRole.SUPPORT, UserRole.HEAD_SUPPORT, UserRole.ADMIN]
    ).first()
    if not profile:
        await message.answer(utils.get_text("access_denied"))
        return

    content = message.text.strip()
    await state.update_data({"content": content})
    await message.answer(utils.get_text("group_choice"), reply_markup=inliene.broadcast_group_keyboard())
    await state.set_state(BroadcastState.group_choice)


async def broadcast_group_done(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    data = await state.get_data()
    selected = data.get("group_choice")

    if not selected:
        await callback.answer(
            "Выберите хотя бы одну группу.",
            show_alert=True
        )
        return

    await callback.message.answer(
        "Введите дату и время так:\n"
        "26.01.2026 14:30"
    )
    await state.set_state(BroadcastState.scheduled_at)
    await callback.answer()


async def broadcast_group_choice(callback: types.CallbackQuery, state: FSMContext):
    profile = models.Profile.objects.filter(
        user__telegram_id=callback.from_user.id,
        role__in=[UserRole.SUPPORT, UserRole.HEAD_SUPPORT, UserRole.ADMIN]
    ).first()

    if not profile:
        await callback.answer(utils.get_text("access_denied"), show_alert=True)
        return

    _, group = callback.data.split("|", 1)

    data = await state.get_data()
    selected: list[str] = data.get("group_choice", [])

    if group == GroupChoice.ALL.value:
        selected = [GroupChoice.ALL.value]
    else:
        if GroupChoice.ALL.value in selected:
            selected.remove(GroupChoice.ALL.value)

        if group in selected:
            selected.remove(group)
        else:
            selected.append(group)

    await state.update_data(group_choice=selected)

    await callback.message.edit_reply_markup(
        reply_markup=inliene.broadcast_group_keyboard(selected)
    )

    await callback.answer()


async def broadcast_scheduled_at_handler(message: types.Message, state: FSMContext):
    profile = models.Profile.objects.filter(
        user__telegram_id=message.from_user.id,
        role__in=[UserRole.SUPPORT, UserRole.HEAD_SUPPORT, UserRole.ADMIN]
    ).first()

    if not profile:
        await message.answer(utils.get_text("access_denied"))
        return

    dt = utils.parse_datetime_ru(message.text)
    if not dt:
        await message.answer(
            "Неверный формат.\n"
            "Введите дату и время так:\n"
            "26.01.2026 14:30"
        )
        return

    await state.update_data({"scheduled_at": dt.isoformat()})
    await message.answer(utils.get_text("show_media_file"), reply_markup=reply.skip_button())
    await state.set_state(BroadcastState.media_file)


async def broadcast_media_file_handler(message: types.Message, state: FSMContext):
    profile = models.Profile.objects.filter(
        user__telegram_id=message.from_user.id,
        role__in=[UserRole.SUPPORT, UserRole.HEAD_SUPPORT, UserRole.ADMIN]
    ).first()

    if not profile:
        await message.answer(utils.get_text("access_denied"))
        return

    if message.text:
        if message.text == "Пропустить шаг":
            await state.update_data({"medias": []})
            await message.answer(utils.get_text("get_btn_title"), reply_markup=reply.skip_button())
            await state.set_state(BroadcastState.get_button_title)
            return

        if message.text == "Далее":
            data = await state.get_data()
            medias = data.get("medias", [])
            medias_sorted = sorted(medias, key=lambda x: x["position"])
            await state.update_data(medias=medias_sorted)
            await message.answer(utils.get_text("get_btn_title"), reply_markup=reply.skip_button())
            await state.set_state(BroadcastState.get_button_title)
            return

    if not message.photo:
        await message.answer(utils.get_text("show_media_file"))
        return

    file_id = message.photo[-1].file_id

    await state.update_data(temp_file_id=file_id)

    await message.answer(
        "Введите позицию для этого файла (например: 1)"
    )

    await state.set_state(BroadcastState.media_position)


async def broadcast_media_position_handler(message: types.Message, state: FSMContext):
    text = message.text.strip()

    if not text.isdigit():
        await message.answer("Введите число позиции.")
        return

    position = int(text)

    data = await state.get_data()
    medias = data.get("medias", [])
    file_id = data.get("temp_file_id")

    if not file_id:
        await message.answer("Ошибка. Отправьте файл заново.")
        await state.set_state(BroadcastState.media_file)
        return

    medias.append({
        "file_id": file_id,
        "position": position
    })

    await state.update_data(
        medias=medias,
        temp_file_id=None
    )

    await message.answer(
        "Файл добавлен.\n"
        "Отправьте следующий файл или нажмите «Далее».",
        reply_markup=reply.next_broadcast_button()
    )
    await state.set_state(BroadcastState.media_file)


async def save_buttons_to_db(state: FSMContext, bot):
    data = await state.get_data()

    title = data.get("title")
    template_id = data.get("template_id")
    content = data.get("content")
    group_choice = data.get("group_choice")
    scheduled_at = parse_datetime(data.get("scheduled_at"))

    buttons = data.get("buttons", [])
    medias = data.get("medias", [])

    try:
        with transaction.atomic():
            broadcast = Broadcast.objects.create(
                title=title,
                template_id=template_id,
                content=content,
                groups=group_choice,
                scheduled_at=scheduled_at
            )

            btn_objects = [
                BroadcastButton(
                    broadcast=broadcast,
                    text=btn.get("title"),
                    url=btn.get("url"),
                    order=btn.get("order", 0)
                )
                for btn in buttons
            ]

            if btn_objects:
                BroadcastButton.objects.bulk_create(btn_objects)

            media_ids = []

            for i, m in enumerate(medias):
                file_id = m.get("file_id")
                order = m.get("position", i)

                django_file = await _save_file_from_telegram(
                    bot,
                    file_id,
                    filename=f"tg_{file_id}.dat"
                )

                media = Media.objects.create(
                    file=django_file,
                    file_id=file_id,
                    order=order,
                    file_type="telegram"
                )

                media_ids.append(media.pk)

            if media_ids:
                broadcast.medias.set(media_ids)


    except Exception as e:
        print("SAVE ERROR:", e)


async def broadcast_button_title_handler(message: types.Message, state: FSMContext):
    text = message.text.strip()

    if text == "Пропустить шаг":
        await state.update_data({"buttons": []})
        await save_buttons_to_db(state, message.bot)

        await message.answer(utils.get_text("skip_btn"), reply_markup=ReplyKeyboardRemove())
        await state.clear()
        return

    if text == "Далее":
        data = await state.get_data()
        buttons = data.get("buttons", [])
        buttons_sorted = sorted(buttons, key=lambda x: x["order"])

        await state.update_data(buttons=buttons_sorted)
        await save_buttons_to_db(state, message.bot)
        await message.answer("Кнопки сохранены ✅", reply_markup=ReplyKeyboardRemove())
        await state.clear()
        return

    profile = models.Profile.objects.filter(
        user__telegram_id=message.from_user.id,
        role__in=[UserRole.SUPPORT, UserRole.HEAD_SUPPORT, UserRole.ADMIN]
    ).first()

    if not profile:
        await message.answer(utils.get_text("access_denied"))
        return

    await state.update_data(temp_button={"title": text})

    await message.answer(utils.get_text("get_button_url"), reply_markup=ReplyKeyboardRemove())
    await state.set_state(BroadcastState.get_button_url)


async def broadcast_button_url_handler(message: types.Message, state: FSMContext):
    profile = models.Profile.objects.filter(
        user__telegram_id=message.from_user.id,
        role__in=[UserRole.SUPPORT, UserRole.HEAD_SUPPORT, UserRole.ADMIN]
    ).first()

    if not profile:
        await message.answer(utils.get_text("access_denied"))
        return

    url = message.text.strip()

    if not url.startswith("https://"):
        await message.answer("Ссылка должна начинаться с https://")
        return

    data = await state.get_data()
    temp_button = data.get("temp_button", {})

    temp_button["url"] = url
    await state.update_data(temp_button=temp_button)

    await message.answer(utils.get_text("get_button_order"))
    await state.set_state(BroadcastState.get_button_order)


async def broadcast_button_order(message: types.Message, state: FSMContext):
    profile = models.Profile.objects.filter(
        user__telegram_id=message.from_user.id,
        role__in=[UserRole.SUPPORT, UserRole.HEAD_SUPPORT, UserRole.ADMIN]
    ).first()

    if not profile:
        await message.answer(utils.get_text("access_denied"))
        return

    text = message.text.strip()

    if not text.isdigit():
        await message.answer("Введите номер позиции кнопки.")
        return

    order = int(text)

    data = await state.get_data()
    buttons = data.get("buttons", [])
    temp_button = data.get("temp_button")

    if not temp_button:
        await message.answer("Ошибка. Начните заново.")
        return

    temp_button["order"] = order
    buttons.append(temp_button)

    await state.update_data(
        buttons=buttons,
        temp_button=None
    )

    await message.answer(
        "Кнопка добавлена.\n"
        "Введите следующую кнопку или нажмите «Далее».",
        reply_markup=reply.next_broadcast_button()
    )

    await state.set_state(BroadcastState.get_button_title)


async def check_kyc_handler(message: types.Message):
    profile = models.Profile.objects.filter(
        user__telegram_id=message.from_user.id,
        role__in=[UserRole.ADMIN, UserRole.PAYMENT_MANAGER]
    ).first()

    if not profile:
        await message.answer("Нет доступа.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) != 2:
        await message.answer("Использование: /check_kyc TOKEN")
        return

    token = parts[1].strip()

    verification = models.Verification.objects.filter(token=token).first()
    if not verification:
        await message.answer("Верификация не найдена.")
        return

    if verification.status == VerificationStatusChoice.VERIFIED:
        status_text = "✅ Верифицирован"
    else:
        status_text = "❌ Не верифицирован"

    text = (
        f"{status_text}\n\n"
        f"ФИО: {verification.fullname or '-'}\n"
        f"Username: @{verification.username if verification.username else '-'}\n"
        f"Телефон: {verification.phone_number or '-'}\n"
        f"Blacklist: {'Да' if verification.is_blacklisted else 'Нет'}\n"
        f"Срок действия: "
        f"{verification.expires_at.strftime('%d.%m.%Y') if verification.expires_at else '—'}"
    )

    await message.answer(text)

    media = []

    if verification.main_page_passport:
        media.append(
            InputMediaPhoto(
                media=FSInputFile(verification.main_page_passport.path),
                caption="Паспорт — главная страница"
            )
        )

    if verification.registration_page_passport:
        media.append(
            InputMediaPhoto(
                media=FSInputFile(verification.registration_page_passport.path),
                caption="Паспорт — страница регистрации"
            )
        )

    if verification.additional_information_passport:
        media.append(
            InputMediaPhoto(
                media=FSInputFile(verification.additional_information_passport.path),
                caption="Паспорт — дополнительная информация"
            )
        )

    if media:
        await message.answer_media_group(media)

    if verification.round_video:
        try:
            await message.answer_video(
                video=FSInputFile(verification.round_video.path),
                caption="Видео подтверждение"
            )
        except Exception as e:
            print(e)


async def mask_handler(message: types.Message):
    profile = models.Profile.objects.filter(
        user__telegram_id=message.from_user.id
    ).first()

    if profile and profile.role in [
        UserRole.SUPPORT,
        UserRole.HEAD_SUPPORT,
        UserRole.VERIFICATOR,
        UserRole.PAYMENT_MANAGER,
        UserRole.ADMIN,
    ]:
        return

    user_text = message.text.strip().lower()
    if not user_text:
        return

    tg_user = models.TelegramUser.objects.filter(
        telegram_id=message.from_user.id
    ).first()

    user_group = tg_user.group if tg_user else GroupChoice.ALL

    masks = models.Mask.objects.all()

    for mask in masks:
        if mask.groups:
            if GroupChoice.ALL not in mask.groups and user_group not in mask.groups:
                continue

        if user_text in mask.text_list:
            mask.count += 1
            mask.save(update_fields=["count"])
            await message.answer(mask.cleaned_content or mask.content)
            return


async def mask_add_handler(message: types.Message, state: FSMContext):
    profile = models.Profile.objects.filter(
        user__telegram_id=message.from_user.id,
        role__in=[UserRole.SUPPORT, UserRole.HEAD_SUPPORT, UserRole.ADMIN]
    ).first()

    if not profile:
        await message.answer("Нет доступа.")
        return

    await state.clear()
    await state.update_data(group_choice=[])

    await message.answer(utils.get_text("group_choice"), reply_markup=inliene.broadcast_group_keyboard())
    await state.set_state(MaskState.groups)


async def mask_add_groups_choice(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected: list[str] = data.get("group_choice", [])

    _, group = callback.data.split("|", 1)

    if group == GroupChoice.ALL.value:
        selected = [GroupChoice.ALL.value]
    else:
        if GroupChoice.ALL.value in selected:
            selected.remove(GroupChoice.ALL.value)

        if group in selected:
            selected.remove(group)
        else:
            selected.append(group)

    await state.update_data(group_choice=selected)

    await callback.message.edit_reply_markup(
        reply_markup=inliene.broadcast_group_keyboard(selected)
    )
    await callback.answer()


async def mask_add_groups_done(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get("group_choice")

    if not selected:
        await callback.answer(
            "Выберите хотя бы одну группу.",
            show_alert=True
        )
        return

    if GroupChoice.ALL.value in selected:
        selected = [GroupChoice.ALL.value]

    await state.update_data(groups=selected)

    await callback.message.answer(
        "Введите ключевые слова маски через запятую:"
    )
    await state.set_state(MaskState.text)
    await callback.answer()


async def mask_add_text_handler(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if not text:
        await message.answer("Введите хотя бы одно ключевое слово.")
        return

    keywords = [t.strip() for t in text.split(",") if t.strip()]
    await state.update_data(text=",".join(keywords))
    await message.answer("Введите контент маски:")
    await state.set_state(MaskState.content)


async def mask_add_content_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    models.Mask.objects.create(
        groups=data.get("groups"),
        text=data.get("text"),
        content=message.text
    )
    await message.answer("Маска успешно создана.")
    await state.clear()


async def mask_find_handler(message: types.Message):
    profile = models.Profile.objects.filter(
        user__telegram_id=message.from_user.id,
        role__in=[UserRole.SUPPORT, UserRole.HEAD_SUPPORT, UserRole.ADMIN]
    ).first()

    if not profile:
        await message.answer("Нет доступа.")
        return

    key = message.text.replace("/mask_find", "").strip().lower()
    if not key:
        await message.answer("Использование: /mask_find слово")
        return

    masks = models.Mask.objects.filter(text__contains=key)
    if not masks.exists():
        await message.answer("Маски не найдены.")
        return

    lines = []
    for m in masks[:10]:
        groups = ",".join(m.groups) if m.groups else "-"
        lines.append(
            f"{m.id}) [{groups}] {m.text} | used: {m.count}"
        )

    await message.answer("\n".join(lines))


async def mask_edit_handler(message: types.Message, state: FSMContext):
    profile = models.Profile.objects.filter(
        user__telegram_id=message.from_user.id,
        role__in=[UserRole.SUPPORT, UserRole.HEAD_SUPPORT, UserRole.ADMIN]
    ).first()

    if not profile:
        await message.answer("Нет доступа.")
        return

    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Использование: /mask_edit ID")
        return

    mask = models.Mask.objects.filter(id=int(parts[1])).first()
    if not mask:
        await message.answer("Маска не найдена.")
        return

    await state.update_data(mask_id=mask.id)
    await message.answer("Введите новый текст ответа:")
    await state.set_state(MaskEditState.content)


async def mask_edit_content_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    mask = models.Mask.objects.filter(id=data["mask_id"]).first()

    if not mask:
        await message.answer("Маска не найдена.")
        await state.clear()
        return

    mask.content = message.text
    mask.save()

    await message.answer("Маска обновлена.")
    await state.clear()


async def mask_edit_groups_handler(message: types.Message, state: FSMContext):
    profile = models.Profile.objects.filter(
        user__telegram_id=message.from_user.id,
        role__in=[UserRole.SUPPORT, UserRole.HEAD_SUPPORT, UserRole.ADMIN]
    ).first()

    if not profile:
        await message.answer("Нет доступа.")
        return

    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Использование: /mask_edit_groups ID")
        return

    mask = models.Mask.objects.filter(id=int(parts[1])).first()
    if not mask:
        await message.answer("Маска не найдена.")
        return

    await state.update_data(
        mask_id=mask.id,
        group_choice=mask.groups or []
    )

    await message.answer(
        utils.get_text("group_choice"),
        reply_markup=inliene.broadcast_group_keyboard(mask.groups or [])
    )
    await state.set_state(MaskEditGroupsState.groups)


async def mask_edit_groups_choice(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected: list[str] = data.get("group_choice", [])

    _, group = callback.data.split("|", 1)

    if group == GroupChoice.ALL.value:
        selected = [GroupChoice.ALL.value]
    else:
        if GroupChoice.ALL.value in selected:
            selected.remove(GroupChoice.ALL.value)

        if group in selected:
            selected.remove(group)
        else:
            selected.append(group)

    await state.update_data(group_choice=selected)

    await callback.message.edit_reply_markup(
        reply_markup=inliene.broadcast_group_keyboard(selected)
    )
    await callback.answer()


async def mask_edit_groups_done(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()

    selected = data.get("group_choice")
    if not selected:
        await callback.answer(
            "Выберите хотя бы одну группу.",
            show_alert=True
        )
        return

    mask = models.Mask.objects.filter(id=data["mask_id"]).first()
    if not mask:
        await callback.message.answer("Маска не найдена.")
        await state.clear()
        return

    if GroupChoice.ALL.value in selected:
        selected = [GroupChoice.ALL.value]

    mask.groups = selected
    mask.save(update_fields=["groups"])
    await callback.message.delete()
    await callback.message.answer("Группы маски обновлены.")
    await state.clear()
    await callback.answer()


async def mask_edit_groups_save_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    mask = models.Mask.objects.filter(id=data["mask_id"]).first()

    if not mask:
        await message.answer("Маска не найдена.")
        await state.clear()
        return

    raw = message.text.upper()
    raw_groups = [g.strip() for g in raw.split(",") if g.strip()]

    valid = []

    for g in raw_groups:
        if g in {"ALL", "ВСЕ", "ВСЕ ГРУППЫ"}:
            valid.append(GroupChoice.ALL.value)
            continue

        if g in GroupChoice.values:
            valid.append(g)

    if not valid:
        await message.answer("Некорректные группы.")
        return

    if GroupChoice.ALL.value in valid:
        valid = [GroupChoice.ALL.value]

    mask.groups = valid
    mask.save(update_fields=["groups"])

    await message.answer("Группы маски обновлены.")
    await state.clear()


async def mask_delete_handler(message: types.Message):
    profile = models.Profile.objects.filter(
        user__telegram_id=message.from_user.id,
        role__in=[UserRole.SUPPORT, UserRole.HEAD_SUPPORT, UserRole.ADMIN]
    ).first()

    if not profile:
        await message.answer("Нет доступа.")
        return

    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Использование: /mask_delete ID")
        return

    mask = models.Mask.objects.filter(id=int(parts[1])).first()
    if not mask:
        await message.answer("Маска не найдена.")
        return

    mask.delete()
    await message.answer("Маска удалена.")


async def add_merchant_handler(message: types.Message, state: FSMContext):
    profile = models.Profile.objects.filter(
        user__telegram_id=message.chat.id,
        role=UserRole.HEAD_SUPPORT
    ).first()

    if not profile:
        await message.answer("Нет доступа")
        return

    parts = message.text.strip().split(maxsplit=1)

    if len(parts) < 2:
        await message.answer(
            "Введите название мерчанта.\n"
            "Пример:\n"
            "/addmerchant Amazon"
        )
        return

    merchant_text = parts[1].strip()
    models.Merchant.objects.create(title=merchant_text)

    await message.answer(f"Мерчант добавлен: {merchant_text}")
