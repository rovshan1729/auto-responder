from aiogram import types, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove
from django.db.models import Q

from bot import utils
from bot.keyboards import reply
from bot.states.states import RegistrationState
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
        utils.get_text("kyc_command_handler"),
        reply_markup=reply.start_verification()
    )


async def get_user_start_verification_handler(message: types.Message, state: FSMContext):
    if message.text == "Приступить к верификации":
        await state.set_state(RegistrationState.phone_number)
        return await message.answer(
            utils.get_text("start_verification_handler"),
            reply_markup=reply.phone_number_button()
        )

    return await message.answer(
        utils.get_text("kyc_command_handler"),
        reply_markup=reply.start_verification()
    )


async def get_phone_number_keyboard_handler(message: types.Message, state: FSMContext):
    if not message.contact:
        return await message.answer(
            utils.get_text("phone_number_keyboard_handler"),
            reply_markup=reply.phone_number_button()
        )

    await state.update_data(phone_number=message.contact.phone_number)
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
            utils.get_text("phone_number_addition_handler_passing"),
            reply_markup=ReplyKeyboardRemove()
        )

    phone = message.contact.phone_number if message.contact else None
    data = await state.get_data()

    if not phone or not utils.is_valid_phone(phone) or phone == data.get("phone_number"):
        return await message.answer(
            utils.get_text("phone_number_addition_handler_error"),
            reply_markup=ReplyKeyboardRemove()
        )

    await state.update_data(add_phone=phone)
    await state.set_state(RegistrationState.email)
    await message.answer(
        utils.get_text("phone_number_addition_handler_accept"),
        reply_markup=ReplyKeyboardRemove()
    )


async def get_email_handler(message: types.Message, state: FSMContext):
    email = message.text.strip()

    if not utils.is_valid_email(email):
        return await message.answer(utils.get_text("email_handler_error"))

    await state.update_data(email=email)
    await state.set_state(RegistrationState.token)
    await message.answer(utils.get_text("email_handler_accept"))


async def get_token_handler(message: types.Message, state: FSMContext):
    token = message.text.strip()

    group = models.TelegramGroup.objects.filter(username__contains=token).first()

    if not group:
        return await message.answer(utils.get_text("get_token_error"))

    await state.update_data(token=group.username)
    await state.set_state(RegistrationState.team_lead)

    await message.answer(utils.get_text("get_token"), reply_markup=reply.skip_button())


async def get_team_lead_handler(message: types.Message, state: FSMContext):
    if message.text == "Пропускать":
        await state.update_data(team_lead=None)
        await state.set_state(RegistrationState.recommend_user)
        return await message.answer(utils.get_text("get_team_lead_passing"))

    lead = models.TelegramUser.objects.filter(
        Q(username=message.text) & Q(is_team_lead=True)
    ).first()

    if not lead:
        return await message.answer(utils.get_text("get_team_lead_error"))

    await state.update_data(team_lead=lead.username)
    await state.set_state(RegistrationState.recommend_user)
    await message.answer(utils.get_text("get_team_lead_passing"))


async def get_recommend_user_handler(message: types.Message, state: FSMContext):
    await state.update_data(recommend_user=message.text)
    await state.set_state(RegistrationState.country)
    await message.answer(utils.get_text("get_recommend_user"), reply_markup=reply.country_button())


async def get_country_handler(message: types.Message, state: FSMContext):
    country = models.Country.objects.filter(title__icontains=message.text).first()

    if not country:
        return await message.answer(utils.get_text("get_country_error"))

    await state.update_data(country=country.title)
    await state.set_state(RegistrationState.fullname)

    await message.answer(utils.get_text("get_country"), reply_markup=ReplyKeyboardRemove())


async def get_user_fullname_handler(message: types.Message, state: FSMContext):
    parts = message.text.split()

    if len(parts) < 3:
        return await message.answer(utils.get_text("get_fullnama_error"))

    await state.update_data(fullname=message.text)
    await state.set_state(RegistrationState.live_address)

    await message.answer(
        utils.get_text("get_fullname")
    )


async def get_user_current_live_address_handler(message: types.Message, state: FSMContext):
    parts = message.text.split("-")

    if len(parts) < 7:
        return await message.answer(utils.get_text("get_current_live_address_error"))

    await state.update_data(user_fullname=message.text)
    await state.set_state(RegistrationState.main_page_passport)

    await message.answer(utils.get_text("get_current_live_address"))


async def _save_photo(message, state, field_name, bot: Bot):
    if not message.photo:
        return None

    file = await bot.get_file(message.photo[-1].file_id)
    await state.update_data({field_name: file})
    return True


async def get_user_main_page_passport_handler(message, state, bot):
    if not await _save_photo(message, state, "main_page_passport", bot):
        return await message.answer(utils.get_text("get_main_page_passport_error"))

    await state.set_state(RegistrationState.registration_page_passport)
    await message.answer(utils.get_text("get_main_page_passport"))


async def get_user_registration_page_passport_handler(message, state, bot):
    if not await _save_photo(message, state, "registration_page_passport", bot):
        return await message.answer(utils.get_text("get_registration_page_passport_error"))

    await state.set_state(RegistrationState.additional_information_passport)
    await message.answer(
        utils.get_text("get_registration_page_passport"),
        reply_markup=reply.skip_button()
    )


async def get_user_additional_information_passport_handler(message, state, bot):
    if message.text == "Пропускать":
        await state.update_data(additional_information_passport=None)

    else:
        if not await _save_photo(message, state, "additional_information_passport", bot):
            return await message.answer(utils.get_text("get_additional_information_passport_error"))

    await state.set_state(RegistrationState.round_video)
    await message.answer(
        utils.get_text("get_additional_information_passport"),
        reply_markup=ReplyKeyboardRemove()
    )


async def get_user_round_video_handler(message, state, bot):
    if not message.video_note:
        return await message.answer(utils.get_text("get_user_round_video_error"))

    file = await bot.get_file(message.video_note.file_id)
    await state.update_data(round_video=file)

    await state.set_state(RegistrationState.geo)
    await message.answer(
        utils.get_text("get_user_round_video")
    )


async def get_user_geo_handler(message, state):
    await state.update_data(geo=message.text)
    await state.set_state(RegistrationState.experience)

    await message.answer(
        utils.get_text("get_user_geo"),
        reply_markup=reply.experience_button()
    )


async def get_user_experience_handler(message, state):
    valid = ["Менее года", "1 год", "2 года", "3 года", "5 лет", "Более 5 лет"]

    if message.text not in valid:
        return await message.answer(utils.get_text("get_experience_error"))

    await state.update_data(experience=message.text)
    await state.set_state(RegistrationState.worked_platform)

    await message.answer(
        utils.get_text("get_experience"),
        reply_markup=ReplyKeyboardRemove()
    )


async def get_user_worked_platform_handler(message, state):
    await state.update_data(worked_platform=message.text)
    await state.set_state(RegistrationState.recommendation_user_contact)

    await message.answer(utils.get_text("get_worked_platform"))


async def get_user_recommendation_user_contact_handler(message, state):
    await state.update_data(recommendation_user_contact=message.text)
    data = await state.get_data()

    text = f"""
    📄 *Анкета пользователя*
    
    👤 *ФИО:* {data.get('fullname')}
    📍 *Адрес:* {data.get('user_fullname')}
    🌍 *Страна:* {data.get('country')}
    
    📱 *Основной номер:* {data.get('phone_number')}
    📱 *Доп. номер:* {data.get('add_phone') or "нет"}
    
    📧 *Email:* {data.get('email')}
    🔑 *Токен группы:* {data.get('token')}
    👨‍💼 *Тимлид:* {data.get('team_lead')}
    🤝 *Рекомендатель:* {data.get('recommend_user')}
    
    🛂 *Главная страница:* {data.get('main_page_passport')}
    🛂 *Прописка:* {data.get('registration_page_passport')}
    🛂 *Доп. инфо:* {data.get('additional_information_passport')}
    
    🎥 *Видео:* {data.get('round_video')}
    
    📌 *ГЕО:* {data.get('geo')}
    💼 *Опыт:* {data.get('experience')}
    🛠 *Платформы:* {data.get('worked_platform')}
    📞 *Контакт рекомендателя:* {data.get('recommendation_user_contact')}
    """

    await message.answer(text)
    await message.answer(
        utils.get_text("get_recommendation_user_contact"),
        reply_markup=reply.verify_button()
    )

    await state.set_state(RegistrationState.verify)


async def user_verification_handler(message, state):
    if message.text == "Перепройти верификацию":
        await message.answer(utils.get_text("verification"), reply_markup=ReplyKeyboardRemove())
        return await state.clear()

    return await message.answer(utils.get_text("verification_error"))
