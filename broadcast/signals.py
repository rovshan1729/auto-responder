import json
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.timezone import now, timedelta

from django_celery_beat.models import PeriodicTask, ClockedSchedule


from .models import Media, Broadcast
from responder.tasks import get_file_id


@receiver(post_save, sender=Media)
def save_media_file_id(sender, instance, created, **kwargs):
    if not instance.file_id:
        get_file_id.delay('Media', instance.pk)



@receiver(post_save, sender=Broadcast)
def save_broadcast_task_id(sender, instance, created, **kwargs):
    print(f"\nWorked on {instance.pk}\n")
    if created:
        scheduled_at = instance.scheduled_at
        if scheduled_at < now():
            scheduled_at = now()

        clocked = ClockedSchedule.objects.create(
            clocked_time=scheduled_at + timedelta(seconds=15),
        )
        task = PeriodicTask.objects.create(
            name=f"Broadcast: #{instance.pk}, scheduled at {str(scheduled_at)}",
            task="broadcast.tasks.send_broadcast",
            clocked=clocked,
            one_off=True,
            args=json.dumps([instance.id]),
        )
        instance.task_id = task.id
        instance.save(update_fields=['task_id'])



