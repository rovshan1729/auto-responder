from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class BroadcastConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'broadcast'
    verbose_name = _("Реклама")

    def ready(self):
        import broadcast.signals
