from pyexpat.errors import messages

from aiogram import types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove
from django.db.models import Q
from responder.choices import VerificationStatusChoice, UserRole
from asgiref.sync import sync_to_async
from django.core.files.base import ContentFile
from datetime import timedelta
from django.utils import timezone

from bot import utils
from bot.keyboards import reply, inliene
from bot.states.states import RegistrationState, WorkerState
from responder import tasks, models


async def track_actions_handler(message: types.Message, message_data: dict):
    tasks.create_user_with_message.delay(message_data)


async def command_handler(message: types.Message):
    command = await utils.get_command(message.text.replace("/", ""))

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

    return await message.answer(
        utils.get_text("kyc_start_message"),
        reply_markup=reply.start_verification()
    )


async def get_phone_number_keyboard_handler(message: types.Message, state: FSMContext):
    if not message.contact:
        return await message.answer(
            utils.get_text("kyc_start_verification_prompt"),
            reply_markup=reply.phone_number_button()
        )

    phone_number = message.contact.phone_number

    await state.update_data(phone_number=phone_number)

    verification, created = await sync_to_async(
        models.Verification.objects.get_or_create
    )(
        chat_id=str(message.from_user.id),
        defaults={
            "phone_number": phone_number,
            "status": VerificationStatusChoice.NO_PASSED
        }
    )
    await state.update_data(verification_id=verification.id)

    await state.set_state(RegistrationState.addition_number)

    await message.answer(
        utils.get_text("phone_number_addition_handler"),
        reply_markup=reply.skip_button()
    )


async def get_phone_number_addition_handler(message: types.Message, state: FSMContext):
    text = message.text.strip()

    if text == "Пропускать":
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
    if message.text == "Пропускать":
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
        return await message.answer(utils.get_text("country_not_found"))

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


async def _save_photo(message, state, field_name, bot: Bot):
    try:
        file = await bot.get_file(message.photo[-1].file_id)
        file_bytes = await message.bot.download_file(file.file_path)
        await state.update_data({field_name: file_bytes, f"{field_name}_id": message.photo[-1].file_id})
        return True
    except Exception as e:
        print(e)


async def get_user_main_page_passport_handler(message, state, bot):
    if not await _save_photo(message, state, "main_page_passport", bot):
        return await message.answer(utils.get_text("passport_main_page_error"))

    await state.set_state(RegistrationState.registration_page_passport)
    await message.answer(utils.get_text("passport_main_page_request"))


async def get_user_registration_page_passport_handler(message, state, bot):
    if not await _save_photo(message, state, "registration_page_passport", bot):
        return await message.answer(utils.get_text("passport_registration_page_error"))

    await state.set_state(RegistrationState.additional_information_passport)
    await message.answer(
        utils.get_text("passport_registration_page_request"),
        reply_markup=reply.skip_button()
    )


async def get_user_additional_information_passport_handler(message, state, bot):
    if message.text == "Пропускать":
        await state.update_data(additional_information_passport=None)

    else:
        if not await _save_photo(message, state, "additional_information_passport", bot):
            return await message.answer(utils.get_text("passport_additional_page_error"))

    await state.set_state(RegistrationState.round_video)
    await message.answer(
        utils.get_text("passport_additional_page_request"),
        reply_markup=ReplyKeyboardRemove()
    )


async def get_user_round_video_handler(message, state, bot):
    if not message.video_note:
        return await message.answer(utils.get_text("round_video_invalid"))

    try:
        file = await bot.get_file(message.video_note.file_id)
        file_bytes = await bot.download_file(file.file_path)

        await state.update_data(round_video=file_bytes, round_video_id=message.video_note.file_id)
        await state.set_state(RegistrationState.geo)

        await message.answer(utils.get_text("round_video_request"))

    except Exception as e:
        print(e)


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


import os
from dotenv import load_dotenv

load_dotenv()


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
        files = {}

        if data.get("main_page_passport"):
            files["main_page_passport"] = ContentFile(
                data["main_page_passport"].read(),
                name=f"{verification.pk}_main_passport.jpg"
            )

        if data.get("registration_page_passport"):
            files["registration_page_passport"] = ContentFile(
                data["registration_page_passport"].read(),
                name=f"{verification.pk}_registration_page_passport.jpg"
            )

        if data.get("additional_information_passport"):
            files["additional_information_passport"] = ContentFile(
                data["additional_information_passport"].read(),
                name=f"{verification.pk}_additional_information_passport.jpg"
            )

        if data.get("round_video"):
            files["round_video"] = ContentFile(
                data["round_video"].read(),
                name=f"{verification.pk}_round_video.mp4"
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
        ADMIN_CHAT_ID = int(os.getenv("ADMIN"))
        multi_files = []
        main_page_passport_id = data["main_page_passport_id"]
        multi_files.append(main_page_passport_id)
        registration_page_passport_id = data["registration_page_passport_id"]
        multi_files.append(registration_page_passport_id)
        additional_information_passport_id = data.get("additional_information_passport_id")
        if additional_information_passport_id:
            multi_files.append(additional_information_passport_id)
        round_video_id = data["round_video_id"]
        group = models.TelegramGroup.objects.filter(title__contains=token).first()
        utils.send_file(ADMIN_CHAT_ID, file_type="video", file_id=round_video_id)

        utils.send_multi_file_by_file_id(ADMIN_CHAT_ID, file_type="photo",
                                         file_ids=multi_files)
        utils.send_text(ADMIN_CHAT_ID, text=text, reply_markup=inliene.check_manager(message.from_user.id))
        # utils.send_multi_file_by_file_id(group.telegram_id, file_type="photo",
        #                                  file_ids=multi_files)
        # utils.send_file(group.telegram_id, file_type="video", file_id=round_video_id)
        # utils.send_text(group.telegram_id, text=text, reply_markup=inliene.check_manager(message.from_user.id))

        verification.username = message.chat.username
        verification.phone_number = phone_number
        verification.add_phone = add_phone
        verification.email = email
        verification.token = token
        verification.team_lead = team_lead
        verification.recommend_user = recommend_user
        verification.recommendation_user_contact = recommendation_user_contact
        verification.status = status
        verification.main_page_passport = files.get("main_page_passport")
        verification.registration_page_passport = files.get("registration_page_passport")
        verification.additional_information_passport = files.get("additional_information_passport")
        verification.round_video = files.get("round_video")
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
    chat_id = callback.data.split("|")[1]

    user = models.Verification.objects.filter(chat_id=chat_id).first()
    if not user:
        return

    # 🔹 Expiration time (updated_at + 90 дней)
    base_time = user.updated_at or timezone.now()
    user.expires_at = base_time + timedelta(days=90)
    user.status = VerificationStatusChoice.VERIFIED
    user.save(update_fields=["expires_at", "status"])

    username = user.fullname or f"@{callback.from_user.username}"
    expired_at = user.expires_at.strftime("%d.%m.%Y %H:%M")
    token = user.token
    group = models.TelegramGroup.objects.filter(title__contains=token).first()
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
    chat_id = int(callback.data.split("|")[1])

    user = models.Verification.objects.filter(chat_id=chat_id).first()
    if not user:
        return

    user.status = VerificationStatusChoice.NoVERIFIED
    user.save(update_fields=["expires_at", "status"])
    token = user.token

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
        chat_id,
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
    await state.set_state(RegistrationState.start)

    await callback.answer()


from django.utils import timezone


async def support_worker_handler(message: types.Message, state: FSMContext):
    await state.clear()
    profile = models.Profile.objects.filter(Q(user__telegram_id=message.chat.id) & Q(role=UserRole.SUPPORT))
    if profile.exists():
        await message.answer(
            utils.get_text("worker_start_message"),
            reply_markup=inliene.worker_choosing_action()
        )


async def worker_start_work_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    chat_id = callback.from_user.id
    profile = models.Profile.objects.filter(user__telegram_id=chat_id)
    await callback.message.delete()

    if profile.exists():
        profile = profile.first()
        worker_data = models.WorkerData.objects.filter(profile=profile)
        if worker_data.exists() and worker_data.first().finish_work_time is not None:
            models.WorkerData.objects.create(profile=profile, start_work_time=timezone.now().isoformat())
            await callback.message.answer(utils.get_text("worker_start_work_message"))
            head_profile = models.Profile.objects.filter(role=UserRole.HEAD_SUPPORT).first()
            text = (f"USER: {callback.from_user.username}\n"
                    f"Start time: {timezone.now().isoformat()}")
            utils.send_text(head_profile.user.telegram_id, text)

        elif not worker_data.exists():
            models.WorkerData.objects.create(profile=profile, start_work_time=timezone.now().isoformat())
            await callback.message.answer(utils.get_text("worker_start_work_message"))
            head_profile = models.Profile.objects.filter(role=UserRole.HEAD_SUPPORT).first()
            text = (f"USER: {callback.from_user.username}\n"
                    f"Start time: {timezone.now().isoformat()}")
            utils.send_text(head_profile.user.telegram_id, text)

        else:
            await callback.message.answer(utils.get_text("worker_doesnt_finish_work"))
    else:
        await callback.message.answer(utils.get_text("default_user"))


async def worker_finish_work_handler(callback: types.CallbackQuery, state: FSMContext):
    chat_id = callback.from_user.id
    work_data = models.WorkerData.objects.filter(profile__user__telegram_id=chat_id, finish_work_time__isnull=True)

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
    await callback.message.delete()
    await callback.message.answer(utils.get_text("choice_merchant"),
                                  reply_markup=inliene.merchant_choosing_inline_button())
    await state.set_state(WorkerState.merchant)


async def get_merchant_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    merchant_id = callback.data.split("|")[1]
    await callback.message.answer(utils.get_text("get_merchant"))
    await state.update_data({
        "merchant_id": merchant_id
    })
    await state.set_state(WorkerState.dispute_count)


async def get_dispute_count_handler(message: types.Message, state: FSMContext):
    count = message.text
    await state.update_data({
        "dispute_count": count
    })
    await message.answer(utils.get_text("get_dispute_count"), reply_markup=inliene.get_dispute_count_inline_button())
    await state.set_state(WorkerState.cycle)
