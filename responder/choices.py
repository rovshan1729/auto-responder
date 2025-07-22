from django.db.models import TextChoices


class ChatMemberStatus(TextChoices):
    MEMBER = 'member'
    ADMINISTRATOR = 'administrator'
    RESTRICTED = 'restricted'
    LEFT = 'left'
    KICKED = 'kicked'


class GroupChoice(TextChoices):
    RUB = 'RUB', 'RUB'
    KZT = 'KZT', 'KZT'
    UZS = 'UZS', 'UZS'
    TJS = 'TJS', 'TJS'
    CNY = 'CNY', 'CNY'
    GEL = 'GEL', 'GEL'
    AMD = 'AMD', 'AMD'
    ALL = 'ВСЕ ГРУППЫ',  'ВСЕ ГРУППЫ'


