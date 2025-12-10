from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove

from bot import utils
# from bot.app import
from bot.keyboards import reply
from bot.states.states import RegistrationState
from responder import tasks


async def track_actions_handler(message: types.Message, message_data: dict):
    tasks.create_user_with_message.delay(message_data)


async def command_handler(message: types.Message):
    command = await utils.get_command(message.text.replace('/', ""))
    if not command:
        return None

    if command['file_id'] or command['file']:
        if command['file_id']:
            photo = command['file_id']
        else:
            photo = types.FSInputFile(command['file'])

        return await message.answer_photo(
            photo=photo,
            caption=command['cleaned_content'],
        )
    return await message.answer(text=command['cleaned_content'])


async def respond_handler(message: types.Message):
    username = message.from_user.username
    credential = username if username else message.from_user.id

    text_list = utils.get_clean_sorted_text_list(message.text)
    mask = await utils.get_mask(text_list, credential)

    message_data = {
        'from_user': {
            'id': message.from_user.id,
            'username': message.from_user.username,
            'first_name': message.from_user.first_name,
            'last_name': message.from_user.last_name,
        },
        'text': message.text,
        'message_id': message.message_id,
    }

    await track_actions_handler(
        message,
        message_data=message_data
    )

    if mask is not None:
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
    await state.set_state(RegistrationState.phone_number)
    await message.answer("Нажмите кнопку ниже, чтобы ввести свой номер телефона.",
                         reply_markup=reply.phone_number_button())


async def get_phone_number_keyboard_handler(message: types.Message, state: FSMContext):
    if not message.contact:
        return await message.answer(
            "Пожалуйста, отправьте свой номер телефона, используя кнопку!",
            reply_markup=reply.phone_number_button()
        )

    phone = message.contact.phone_number
    await state.update_data(phone_number=phone)
    await state.set_state(RegistrationState.addition_number)

    await message.answer(
        "Если у вас есть дополнительный номер телефона, введите его, в противном случае нажмите «Пропустить».",
        reply_markup=reply.skip_button()
    )


async def get_phone_number_addition_handler(message: types.Message, state: FSMContext):
    text = message.text.strip()

    if text == "Пропускать":
        await state.update_data(add_phone=None)
        await message.answer(
            "Пропустили еще один номер!",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()
        return

    if message.contact:
        phone = message.contact.phone_number
    else:
        phone = text

    phone_number = await state.get_data()
    if not utils.is_valid_phone(phone) or phone_number["phone_number"] == phone:
        return await message.answer("Неверный номер! Пожалуйста, отправьте повторно.",
                                    reply_markup=ReplyKeyboardRemove())

    await state.update_data(add_phone=phone)
    await message.answer("Дополнительный номер получен!", reply_markup=ReplyKeyboardRemove())
