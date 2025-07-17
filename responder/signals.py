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

    if not created and not instance.is_retry:
        return

    if instance.message.group_id:
        chat_id = instance.message.group.telegram_id
    else:
        chat_id = instance.message.user.telegram_id

    reply(
        chat_id=chat_id,
        text=instance.cleaned_text,
        reply_to_message_id=instance.message.message_id
    )
    instance.is_retry = False
    instance.save(update_fields=['is_retry'])

    instance.message.is_marked = True
    instance.message.answer = instance.cleaned_text
    instance.message.save(update_fields=['is_marked', 'answer',  'answer_list'])


