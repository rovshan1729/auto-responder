from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import TelegramCommand
from .tasks import get_file_id

@receiver(post_save, sender=TelegramCommand)
def save_telegram_command_file_id(sender, instance, created, **kwargs):
    if not instance.file_id:
        get_file_id.delay('TelegramCommand', instance.pk)
