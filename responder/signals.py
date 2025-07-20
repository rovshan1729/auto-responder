from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import TelegramCommand, ReplyMessage
from .tasks import get_file_id

from bot.utils.methods import reply


@receiver(post_save, sender=TelegramCommand)
def save_telegram_command_file_id(sender, instance, created, **kwargs):
    if not instance.file_id:
        get_file_id.delay('TelegramCommand', instance.pk)


@receiver(post_save, sender=ReplyMessage)
def send_reply_message(sender, instance: ReplyMessage, created, **kwargs):
    # if not created and not instance.is_retry:
    #     return
    print(f"\nWorked send reply message signal \n")
    try:
        chat_id = instance.message.group.telegram_id
        print(f"Chat_id in group: {chat_id}")
    except Exception as e:
        print(f"{e = }")
        chat_id = instance.message.user.telegram_id
        print(f"Chat_id in user: {chat_id}")

    response = reply(
        chat_id=chat_id,
        text=instance.cleaned_text,
        reply_to_message_id=instance.message.message_id
    )
    # try:
    #     json_data = response.json()
    #     print(f"{json_data = }")
    # except Exception as e:
    #     print(f"{e = }")

    if response.status_code != 200:
        return
    # instance.is_retry = False
    # instance.save(update_fields=['is_retry'])

    instance.message.is_marked = True
    instance.message.answer = instance.cleaned_text
    instance.message.save(update_fields=['is_marked', 'answer', 'answer_list'])
