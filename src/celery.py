import os
from celery import Celery
from celery.schedules import crontab
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', "src.settings")

app = Celery("src")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "run-every-hour-task": {
        "task": "responder.tasks.trigger_telegram_sync",
        "schedule": timedelta(minutes=2),
    }
}
