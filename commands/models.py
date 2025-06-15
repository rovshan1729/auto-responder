from django_celery_beat.models import PeriodicTask, CrontabSchedule, IntervalSchedule
from django.utils.translation import gettext_lazy as _


# class PeriodicTaskProxy(PeriodicTask):
#     class Meta:
#         proxy = True
#         verbose_name = _("Периодическая задача")
#         verbose_name_plural = _("Периодические задачи")
#
#
# class CrontabScheduleProxy(CrontabSchedule):
#     class Meta:
#         proxy = True
#         verbose_name = _("Расписание (cron)")
#         verbose_name_plural = _("Расписания (cron)")
