from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ResponderConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'responder'
    verbose_name = _("Автоответчик")

    def ready(self):
        import responder.signals
