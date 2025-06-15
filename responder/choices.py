from django.db.models import TextChoices


class ChatMemberStatus(TextChoices):
    MEMBER = 'member'
    ADMINISTRATOR = 'administrator'
    RESTRICTED = 'restricted'
    LEFT = 'left'
    KICKED = 'kicked'


