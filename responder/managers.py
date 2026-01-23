from django.db import models
from responder.choices import VerificationStatusChoice


class CurrentVerificationManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(
            status__in=[
                VerificationStatusChoice.NO_PASSED,
                VerificationStatusChoice.WAITING,
            ]
        )


class ArchivedVerificationManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(
            status=VerificationStatusChoice.ARCHIVE
        )
