import os
import time
import logging

from celery import shared_task
from django.conf import settings

from responder import models as r_models
from broadcast import models as b_models
from bot import utils

BASE_DIR = settings.BASE_DIR

logger = logging.getLogger(__name__)


@shared_task
def create_json_file(data: dict, type: str):
    os.makedirs(f"{BASE_DIR}/messages", exist_ok=True)
    if type == 'message':
        path_file = f"{BASE_DIR}/messages/{type}_{data['message_id']}.json"
    else:
        i = 1
        path_file = f"{BASE_DIR}/messages/{type}_{data['chat']['id']}_{data.get('new_chat_member', {}).get('status', 'None')}_{i}.json"
        while os.path.exists(path_file):
            file_name_with_i, extension = os.path.splitext(path_file)
            file_name = tuple(str(file_name_with_i).split(f'_{i}'))[0]
            file_name += f"_{i}"
            path_file = f"{file_name}{extension}"

    utils.create_json_file(
        path_file=path_file,
        data=data,
    )


@shared_task
def create_user_with_message(message_data: dict):
    user = r_models.TelegramUser.objects.filter(
        telegram_id=message_data['from_user']['id']
    ).first()

    if user is None:
        user = r_models.TelegramUser.objects.create(
            telegram_id=message_data['from_user']['id'],
            username=message_data['from_user']['username'],
            first_name=message_data['from_user']['first_name'],
            last_name=message_data['from_user']['last_name']
        )

    r_models.TelegramMessage.objects.create(
        user=user,
        text=message_data['text'],
        message_id=message_data['message_id'],
        data=message_data
    )


@shared_task
def create_user_with_message_on_group(message_data: dict):
    print(f"{message_data['text'] = }")
    group = r_models.TelegramGroup.objects.filter(
        telegram_id=message_data['chat']['id']
    ).values_list('id', flat=True).first()

    if group is None:
        response = utils.get_chat_member(
            chat_id=message_data['chat']['id'],
            user_id=settings.API_TOKEN.split(":")[0]
        )
        status = "member"
        response_data = response.json()
        if response.status_code == 200:
            status = response_data.get("result", {}).get("status")

        group = r_models.TelegramGroup.objects.create(
            telegram_id=message_data['chat']['id'],
            username=message_data['chat']['username'],
            title=message_data['chat']['title'],
            status=status,
        )
        group = group.id

    user = r_models.TelegramUser.objects.filter(
        telegram_id=message_data['from_user']['id']
    ).first()
    if user is None:
        user = r_models.TelegramUser.objects.create(
            telegram_id=message_data['from_user']['id'],
            username=message_data['from_user']['username'],
            first_name=message_data['from_user']['first_name'],
            last_name=message_data['from_user']['last_name']
        )

    if not user.groups.filter(id=group).exists():
        user.groups.add(group)

    r_models.TelegramMessage.objects.create(
        group_id=group,
        user=user,
        text=message_data['text'],
        message_id=message_data['message_id'],
        data=message_data
    )


@shared_task
def get_file_id(class_name: str, class_id: int):
    update_fields = []
    data = r_models.Data.get_solo()

    if class_name == "Media":
        obj = b_models.Media.objects.filter(id=class_id).first()
    else:
        obj = r_models.TelegramCommand.objects.filter(id=class_id).first()

    if not obj:
        return

    extension = obj.file.name.split(".")[-1].lower()
    file_type = utils.get_file_type(extension)
    file_path = str(os.path.join(settings.MEDIA_ROOT, obj.file.name))

    for i in range(3):
        try:
            response = utils.send_file(
                chat_id=data.channel_id,
                file_path=file_path,
                file_type=file_type,
            )

            if response.status_code == 200:
                response_data = response.json()

                if file_type == 'photo':
                    photo = response_data.get('result', {}).get('photo', [])
                    file_id = None
                    if photo:
                        file_id = photo[0].get('file_id')
                else:
                    file_id = response_data.get('result', {}).get(f'{file_type}', {}).get('file_id')

                obj.file_id = file_id
                update_fields.append('file_id')

                if class_name == "Media":
                    obj.file_type = file_type
                    update_fields.append('file_type')

                obj.save(update_fields=update_fields)
                break
            else:
                time.sleep(2)
        except Exception as e:
            logger.error(f"Exception while getting file id: {e}")
            time.sleep(2)


@shared_task
def create_faq(message_text: str, mask_id: int = None, telegram_id: int | str = None):
    mask = None if not mask_id else r_models.Mask.objects.filter(id=mask_id).first()

    question = message_text
    answer = None
    if mask is not None:
        question = mask.text
        answer = mask.content

    faq = r_models.FAQ.objects.filter(question=question).first()
    if faq is None:
        r_models.FAQ.objects.create(
            question=question,
            answer=answer,
            count=1
        )
    else:
        faq.count += 1
        faq.save(update_fields=["count"])


@shared_task
def mark_message(message_id: int, sender_id: int | str, mask:str, where="private"):
    time.sleep(5)
    if where == "private":
        message = r_models.TelegramMessage.objects.filter(
            message_id=message_id,
            user__telegram_id=sender_id
        ).first()
    else:
        message = r_models.TelegramMessage.objects.filter(
            message_id=message_id,
            group__telegram_id=sender_id
        ).first()
    if message is None:
        return

    message.is_marked = True
    message.answer = mask
    message.save(update_fields=["is_marked", "answer"])


@shared_task
def send_reply_message():
    pass

