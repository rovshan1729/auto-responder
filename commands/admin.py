
from django.contrib import admin
from django_celery_beat.admin import (
    PeriodicTaskAdmin,
    CrontabScheduleAdmin,
)
from django_celery_beat.models import PeriodicTask, CrontabSchedule

PeriodicTask._meta.verbose_name = "Периодическая задача"
PeriodicTask._meta.verbose_name_plural = "Периодические задачи"
CrontabSchedule._meta.verbose_name = "Расписание (cron)"
CrontabSchedule._meta.verbose_name = "Расписания (cron)"

# from .models import (
#     PeriodicTaskProxy,
#     CrontabScheduleProxy,
# )
#
# admin.site.register(CrontabScheduleProxy, CrontabScheduleAdmin)
# admin.site.register(PeriodicTaskProxy, PeriodicTaskAdmin)






