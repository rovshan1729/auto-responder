from aiogram import types
from aiogram.fsm.context import FSMContext

from responder import tasks
from bot import utils


async def track_actions_handler(message: types.Message, message_data: dict):
    tasks.create_user_with_message_on_group.delay(message_data)


async def listen_message_handler(message: types.Message, state: FSMContext):
    message_data = message.model_dump()
    # tasks.create_json_file.delay(message_data, 'message')

    data = await utils.get_data_model()
    if message.text and data.is_sleep is False:
        await respond_handler(message)

    await track_actions_handler(message, message_data)


async def command_handler(message: types.Message, state: FSMContext):
    command = await utils.get_command(
        message.text.replace('/', "").split("@")[0]
    )

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
    group_id = message.chat.id

    text_list = utils.get_clean_sorted_text_list(message.text)
    mask = await utils.get_mask(text_list, credential, group_id)

    if mask is not None:
        await message.reply(mask.cleaned_content)
        tasks.create_faq.delay(message.text, mask.id)
        tasks.mark_message(message.message_id)

    elif "?" in message.text:
        tasks.create_faq.delay(message.text)


async def my_chat_member_update_handler(event: types.ChatMemberUpdated):
    event_data = event.model_dump()
    tasks.create_json_file.delay(event_data, 'my_status')

    await utils.get_or_create_chat(
        telegram_id=event.chat.id,
        defaults={
            'username': event.chat.username,
            'title': event.chat.title,
            'status': event.new_chat_member.status,
        }
    )


async def chat_member_update_handler(event: types.ChatMemberUpdated, state: FSMContext):
    event_data = event.model_dump()
