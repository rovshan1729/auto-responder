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
    TRANSGRAN = 'TRANSGRAN', 'TRANSGRAN'
    ALL = 'ВСЕ ГРУППЫ', 'ВСЕ ГРУППЫ'


class VerificationStatusChoice(TextChoices):
    NO_PASSED = "Не пройдено", "Не пройдено"
    WAITING = "В ожидании", "В ожидании"
    VERIFIED = "Верифицирован", "Верифицирован"
    NoVERIFIED = "Не верифицирован", "Не верифицирован"
    ARCHIVE = "Архив", "Архив"
