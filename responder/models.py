from django.db import models
from django.urls import reverse
from django.contrib.postgres.fields import ArrayField

from tinymce.models import HTMLField
from solo.models import SingletonModel

from .base import BaseModel
from .choices import ChatMemberStatus, GroupChoice, VerificationStatusChoice, AdminFieldType
from responder.managers import CurrentVerificationManager, ArchivedVerificationManager
from bot import utils


class Data(SingletonModel):
    channel_id = models.BigIntegerField(
        help_text="ID Канала для сохранения медиа файлов.",
        blank=True,
        null=True,
        verbose_name="ID Канала",
        editable=False
    )
    is_sleep = models.BooleanField(
        default=False,
        help_text="включения/выключения бота",
        verbose_name="Спящий режим"
    )

    class Meta:
        verbose_name = 'Настройки'

    def __str__(self):
        return "Data Model"


class TelegramGroup(BaseModel):
    telegram_id = models.BigIntegerField(
        unique=True,
        verbose_name="Телеграм ID"
    )
    username = models.CharField(
        max_length=63,
        unique=True,
        blank=True,
        null=True,
        verbose_name="Имя пользователя группы"
    )
    title = models.CharField(
        max_length=63,
        blank=True,
        null=True,
        verbose_name="Название группы"
    )
    status = models.CharField(
        max_length=15,
        choices=ChatMemberStatus.choices,
        verbose_name="Статус бота в группе"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активен"
    )

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Телеграм Группа'
        verbose_name_plural = 'Телеграм Группы'
        # abstract = True

    def __str__(self):
        return str(self.username) if self.username else str(self.title)


class TelegramUser(BaseModel):
    telegram_id = models.BigIntegerField(
        unique=True,
        verbose_name="Телеграм ID"
    )
    groups = models.ManyToManyField(
        TelegramGroup,
        related_name='users',
        verbose_name="Группы"
    )
    username = models.CharField(
        max_length=63,
        unique=True,
        blank=True,
        null=True,
        verbose_name="Имя пользователя"
    )
    first_name = models.CharField(
        max_length=63,
        blank=True,
        null=True,
        verbose_name="Имя"
    )
    last_name = models.CharField(
        max_length=63,
        blank=True,
        null=True,
        verbose_name="Фамилия"
    )
    is_blocked = models.BooleanField(
        default=False,
        verbose_name="Заблокирован"
    )

    class Meta:
        # ordering = ('-created_at',)
        verbose_name = 'телеграм пользователя'
        verbose_name_plural = 'Телеграм Пользователи'
        # abstract = True

    def get_admin_url(self):
        return reverse(
            f"admin:{self._meta.app_label}_{self._meta.model_name}_change",
            args=[self.pk]
        )

    def __str__(self):
        return self.username if self.username else self.first_name


class TelegramMessage(BaseModel):
    group = models.ForeignKey(
        TelegramGroup,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='messages',
        verbose_name="Группа"
    )
    user = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name="Пользователь"
    )
    text = models.CharField(
        max_length=4095,
        blank=True,
        null=True,
        verbose_name="Текст"
    )
    text_list = ArrayField(
        models.CharField(max_length=255),
        blank=True,
        null=True,
        verbose_name="Фильтрованный текст"
    )
    answer = models.CharField(
        max_length=4095,
        blank=True,
        null=True,
        verbose_name="Ответ"
    )
    answer_list = ArrayField(
        models.CharField(max_length=255),
        blank=True,
        null=True,
        editable=False
    )
    message_id = models.BigIntegerField(
        verbose_name="ID сообщении"
    )
    is_marked = models.BooleanField(
        default=False,
        verbose_name="Отвечено"
    )
    data = models.JSONField(
        blank=True,
        null=True,
        verbose_name="Дата"
    )

    class Meta:
        ordering = ('-created_at',)
        verbose_name = "Телеграм сообщения"
        verbose_name_plural = "Телеграм Сообщения"
        # abstract = True

    def get_admin_url(self):
        return reverse(
            f"admin:{self._meta.app_label}_{self._meta.model_name}_change",
            args=[self.pk]
        )

    def save(self, *args, **kwargs):
        if self.text:
            self.text_list = utils.get_clean_sorted_text_list(self.text)
        if self.answer:
            self.answer_list = utils.get_clean_sorted_text_list(self.answer)
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.message_id)


class ReplyMessage(BaseModel):
    message = models.OneToOneField(
        TelegramMessage,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="reply"
    )
    text = HTMLField(verbose_name="Текст")
    cleaned_text = models.TextField(
        blank=True,
        null=True,
        editable=False
    )
    is_retry = models.BooleanField(
        default=False,
        verbose_name="Отправить заново"
    )
    is_sent = models.BooleanField(
        default=False,
        verbose_name="Отправлено",
        editable=False
    )

    class Meta:
        verbose_name = "Ответить"
        verbose_name_plural = "Ответить"

    def save(self, *args, **kwargs):
        self.cleaned_text = utils.clean_from_html_v3(self.text)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Reply Message (pk = {self.pk})"


class TelegramCommand(BaseModel):
    command = models.CharField(
        max_length=15,
        unique=True,
        verbose_name="Название"
    )
    description = models.CharField(
        max_length=63,
        verbose_name="Описание"
    )
    content = HTMLField(
        verbose_name="Контент"
    )
    cleaned_content = models.TextField(
        blank=True,
        null=True,
        editable=False
    )
    file = models.ImageField(
        upload_to="images/%Y/%m/%d",
        blank=True,
        null=True,
        verbose_name="Фото"
    )
    file_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Файл ID"

    )

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'команду'
        verbose_name_plural = 'Телеграм команды'
        # abstract = True

    def get_admin_url(self):
        return reverse(
            f"admin:{self._meta.app_label}_{self._meta.model_name}_change",
            args=[self.pk]
        )

    def save(self, *args, **kwargs):
        self.cleaned_content = utils.clean_from_html_v3(self.content)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.command


class Mask(BaseModel):
    groups = ArrayField(
        models.CharField(max_length=31, choices=GroupChoice.choices),
        blank=True,
        null=True,
        default=list
    )
    # groups = models.ManyToManyField(
    #     TelegramGroup,
    #     blank=True,
    #     related_name='masks',
    # )
    text = models.CharField(
        max_length=4095,
        verbose_name="Текст"
    )
    text_list = ArrayField(
        models.CharField(max_length=255),
        blank=True,
        editable=False
    )
    content = HTMLField(
        verbose_name="Контент",
        help_text="Текст ответа"
    )
    cleaned_content = models.TextField(
        blank=True,
        null=True,
        editable=False
    )
    count = models.BigIntegerField(
        default=0,
        editable=False
    )

    class Meta:
        ordering = ('-created_at',)
        verbose_name = "маску"
        verbose_name_plural = "Маски"
        # abstract = True

    def get_admin_url(self):
        return reverse(
            f"admin:{self._meta.app_label}_{self._meta.model_name}_change",
            args=[self.pk]
        )

    def save(self, *args, **kwargs):
        self.cleaned_content = utils.clean_from_html_v3(self.content)
        self.text_list = utils.get_clean_sorted_text_list(self.text)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.text


class FAQ(BaseModel):
    question = models.CharField(max_length=4095, verbose_name="Вопрос", editable=False)
    answer = models.CharField(max_length=4095, verbose_name="Ответ", blank=True, null=True, editable=False)
    count = models.BigIntegerField(default=0, editable=False)

    class Meta:
        ordering = ('-count',)
        verbose_name = "Аналитика"
        verbose_name_plural = "Аналитика"

    def __str__(self):
        return self.question


class Country(BaseModel):
    title = models.CharField(max_length=256, verbose_name="Страна")

    def __str__(self):
        return self.title


class StaticText(BaseModel):
    code = models.CharField(max_length=256, unique=True)
    text = models.TextField()

    def __str__(self):
        return f"{self.code} - {self.text}"


class Verification(BaseModel):
    chat_id = models.CharField(max_length=128, unique=True)

    fullname = models.CharField(max_length=255, null=True, blank=True)

    live_address = models.TextField(null=True, blank=True)

    phone_number = models.CharField(max_length=20, null=True, blank=True)
    add_phone = models.CharField(max_length=20, null=True, blank=True)

    email = models.EmailField()
    experience = models.CharField(max_length=50, null=True, blank=True)

    token = models.CharField(max_length=255, unique=True, null=True, blank=True)

    team_lead = models.CharField(max_length=100, null=True, blank=True)
    recommend_user = models.CharField(max_length=100, null=True, blank=True)

    status = models.CharField(
        max_length=50,
        choices=VerificationStatusChoice.choices
    )

    geo = models.TextField(null=True, blank=True)
    worked_platform = models.TextField(null=True, blank=True)
    recommendation_user_contact = models.TextField(null=True, blank=True)
    additionally = models.TextField(null=True, blank=True)
    commentary = models.TextField(null=True, blank=True)

    main_page_passport = models.ImageField(upload_to="verification/", null=True, blank=True)
    registration_page_passport = models.ImageField(upload_to="verification/", null=True, blank=True)
    additional_information_passport = models.ImageField(upload_to="verification/", null=True, blank=True)
    round_video = models.FileField(upload_to="verification/", null=True, blank=True)

    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE, null=True, blank=True
    )

    def __str__(self):
        return f"{self.fullname} | {self.phone_number}"


class AllVerification(Verification):
    class Meta:
        proxy = True
        verbose_name = "Все верификации"
        verbose_name_plural = "Все верификации"


class CurrentVerification(Verification):
    objects = CurrentVerificationManager()

    class Meta:
        proxy = True
        verbose_name = "Текущие верификации"
        verbose_name_plural = "Текущие верификации"


class ArchivedVerification(Verification):
    objects = ArchivedVerificationManager()

    class Meta:
        proxy = True
        verbose_name = "Архив"
        verbose_name_plural = "Архив"


class VerificationAdminField(models.Model):
    verification = models.ForeignKey(
        Verification,
        on_delete=models.CASCADE,
        related_name="admin_fields"
    )

    label = models.CharField(
        max_length=255,
        verbose_name="Название поля"
    )

    field_type = models.CharField(
        max_length=50,
        choices=AdminFieldType.choices,
        default=AdminFieldType.TEXT
    )

    value = models.TextField(
        null=True,
        blank=True,
        verbose_name="Значение"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Дополнительное поле"
        verbose_name_plural = "Дополнительные поля"

    def __str__(self):
        return f"{self.label} ({self.get_field_type_display()})"
