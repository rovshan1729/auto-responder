from pyexpat.errors import messages

from aiogram import types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove
from django.db.models import Q
from responder.choices import VerificationStatusChoice, UserRole, DisputeStatus
from asgiref.sync import sync_to_async
from django.core.files.base import ContentFile
from datetime import timedelta, datetime
from django.utils import timezone

from bot import utils
from bot.keyboards import reply, inliene
from bot.states.states import RegistrationState, WorkerState, HeadReportState, BroadcastState
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
    profile = models.Profile.objects.filter(
        user__telegram_id=callback.from_user.id,
        role__in=[UserRole.SUPPORT, UserRole.ADMIN]
    ).first()
    if not profile:
        await callback.answer("Нет доступа", show_alert=True)
        return

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
    profile = models.Profile.objects.filter(
        user__telegram_id=callback.from_user.id,
        role__in=[UserRole.SUPPORT, UserRole.ADMIN]
    ).first()
    if not profile:
        await callback.answer("Нет доступа", show_alert=True)
        return

    await callback.message.delete()
    await callback.message.answer(utils.get_text("choice_merchant"),
                                  reply_markup=inliene.merchant_choosing_inline_button())
    await state.set_state(WorkerState.merchant)


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
    await state.set_state(WorkerState.dispute_count)


async def get_dispute_count_handler(message: types.Message, state: FSMContext):
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
    disputes.append({
        "merchant_id": merchant_id,
        "dispute_count": count,
        "status": "new"
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
        await callback.message.answer(utils.get_text("choice_merchant"),
                                      reply_markup=inliene.merchant_choosing_inline_button())
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
        await message.answer("Нет доступа", show_alert=True)
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

    report, _ = models.WorkerShiftReport.objects.get_or_create(worker_data=work_data)

    report.comment = problem_text_input
    report.is_submitted = True
    report.submitted_at = timezone.now()
    report.save(update_fields=["comment", "is_submitted", "submitted_at"])

    for d in disputes:
        merchant_id = d.get("merchant_id")
        count = d.get("dispute_count")

        if not merchant_id or count is None:
            continue

        models.WorkerDispute.objects.create(
            report=report,
            merchant_id=int(merchant_id),
            count=int(count),
            status=DisputeStatus.NEW
        )

    work_data.finish_work_time = timezone.now()
    work_data.save(update_fields=["finish_work_time"])

    head_profile = models.Profile.objects.filter(role=UserRole.HEAD_SUPPORT).first()
    if head_profile:
        username = message.from_user.username or message.from_user.full_name

        now_str = timezone.localtime(timezone.now()).strftime("%d.%m.%Y %H:%M:%S")

        db_disputes = report.disputes.select_related("merchant").all()

        grouped = {}
        # merchant_title => {resolved:0, new:0, unresolved:0}
        for item in db_disputes:
            title = item.merchant.title

            if title not in grouped:
                grouped[title] = {
                    "resolved": 0,
                    "new": 0,
                    "unresolved": 0
                }

            if item.status == DisputeStatus.RESOLVED:
                grouped[title]["resolved"] += item.count
            elif item.status == DisputeStatus.NEW:
                grouped[title]["new"] += item.count
            elif item.status == DisputeStatus.UNRESOLVED:
                grouped[title]["unresolved"] += item.count

        lines = []
        for merchant_title in sorted(grouped.keys()):
            r = grouped[merchant_title]["resolved"]
            n = grouped[merchant_title]["new"]
            u = grouped[merchant_title]["unresolved"]

            lines.append(f"{merchant_title}: решённые {r} новые {n} нерешённые {u}")

        merchants_block = "\n".join(lines) if lines else "Нет диспутов"

        head_text = (
            f"Дата и время: {now_str}\n"
            f"Саппорт: @{username}\n\n"
            f"{merchants_block}\n\n"
            f"Проблема:\n{report.comment or '-'}"
        )

        utils.send_text(head_profile.user.telegram_id, head_text)

    await message.answer(utils.get_text("the_shift_assigned"))
    await state.clear()


async def get_add_problem_support_handler(callback: types.CallbackQuery, state: FSMContext):
    profile = models.Profile.objects.filter(
        user__telegram_id=callback.from_user.id,
        role__in=[UserRole.SUPPORT, UserRole.ADMIN]
    ).first()
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

    disputes = models.WorkerDispute.objects.filter(
        report_id__in=report_ids
    ).select_related("merchant")

    if not disputes.exists():
        await message.answer(utils.get_text("access_denied"))
        await state.clear()
        return

    grouped = {}
    total = {"resolved": 0, "new": 0, "unresolved": 0}

    for d in disputes:
        title = d.merchant.title

        if title not in grouped:
            grouped[title] = {"resolved": 0, "new": 0, "unresolved": 0}

        if d.status == DisputeStatus.RESOLVED:
            grouped[title]["resolved"] += d.count
            total["resolved"] += d.count
        elif d.status == DisputeStatus.NEW:
            grouped[title]["new"] += d.count
            total["new"] += d.count
        elif d.status == DisputeStatus.UNRESOLVED:
            grouped[title]["unresolved"] += d.count
            total["unresolved"] += d.count

    lines = []
    lines.append(f"Отчет по диспутам")
    lines.append(f"Период: {date_from.strftime('%d.%m.%Y')} - {date_to.strftime('%d.%m.%Y')}")
    lines.append("")
    lines.append("По мерчантам:")

    for merchant_title in sorted(grouped.keys()):
        r = grouped[merchant_title]["resolved"]
        n = grouped[merchant_title]["new"]
        u = grouped[merchant_title]["unresolved"]
        lines.append(f"{merchant_title}: решённые {r} новые {n} нерешённые {u}")

    lines.append("")
    lines.append(
        f"ИТОГО: решённые {total['resolved']} новые {total['new']} нерешённые {total['unresolved']}"
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
    await message.answer(utils.get_text("show_broadcast"))
    await state.set_state(BroadcastState.text)


async def broadcast_text_handler(message: types.Message, state: FSMContext):
    profile = models.Profile.objects.filter(
        user__telegram_id=message.from_user.id,
        role__in=[UserRole.SUPPORT, UserRole.HEAD_SUPPORT, UserRole.ADMIN]
    ).first()

    if not profile:
        return

    text = message.text.strip()

    users = models.Profile.objects.exclude(
        role__in=[
            UserRole.SUPPORT,
            UserRole.HEAD_SUPPORT,
            UserRole.VERIFICATOR,
            UserRole.PAYMENT_MANAGER,
            UserRole.ADMIN,
        ]
    ).select_related("user")

    sent = 0
    for p in users:
        try:
            utils.send_text(p.user.telegram_id, text)
            sent += 1
        except:
            pass

    await message.answer(f"Рассылка отправлена ({sent} пользователей).")
    await state.clear()
