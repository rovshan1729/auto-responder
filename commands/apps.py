from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CommandsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'commands'
    verbose_name = _("периодические задачи")

    def ready(self):
        import responder.signals