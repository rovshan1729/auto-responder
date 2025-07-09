from aiogram import types
from bot import utils
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

    message_data = message.model_dump()
    await track_actions_handler(message, message_data)

    if mask is not None:
        await message.reply(mask.cleaned_content)
        tasks.create_faq.delay(message.text, mask.id)

    elif "?" in message.text:
        tasks.create_faq.delay(message.text)
        tasks.mark_message(message.message_id)








