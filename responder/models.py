from django.db import models
from django.urls import reverse
from django.contrib.postgres.fields import ArrayField

from tinymce.models import HTMLField
from solo.models import SingletonModel

from .base import BaseModel
from .choices import ChatMemberStatus
from bot import utils


class Data(SingletonModel):
    channel_id = models.BigIntegerField(help_text="Private channel id", blank=True, null=True, editable=False)
    is_sleep = models.BooleanField(default=False, help_text="включения/выключения бота", verbose_name="Спящий режим")

    class Meta:
        verbose_name = 'Настройки'

    def __str__(self):
        return "Data Model"


class TelegramGroup(BaseModel):
    telegram_id = models.BigIntegerField(unique=True, verbose_name="Телеграм ID")
    username = models.CharField(max_length=63, unique=True, blank=True, null=True, verbose_name="Имя пользователя группы")
    title = models.CharField(max_length=63, blank=True, null=True, verbose_name="Название группы")
    status = models.CharField(max_length=15, choices=ChatMemberStatus.choices, verbose_name="Статус бота в группе")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Телеграм Группа'
        verbose_name_plural = 'Телеграм Группы'
        # abstract = True

    def __str__(self):
        return str(self.username) if self.username else str(self.title)


class TelegramUser(BaseModel):
    telegram_id = models.BigIntegerField(unique=True, verbose_name="Телеграм ID")
    groups = models.ManyToManyField(TelegramGroup, related_name='users', verbose_name="Группы")
    username = models.CharField(max_length=63, unique=True, blank=True, null=True, verbose_name="Имя пользователя")
    first_name = models.CharField(max_length=63, blank=True, null=True, verbose_name="Имя")
    last_name = models.CharField(max_length=63, blank=True, null=True, verbose_name="Фамилия")
    is_blocked = models.BooleanField(default=False, verbose_name="Заблокирован")

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
    group = models.ForeignKey(TelegramGroup, on_delete=models.SET_NULL, blank=True, null=True,
                              related_name='messages', verbose_name="Группа")
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name='messages',
                             verbose_name="Пользователь")
    text = models.CharField(max_length=4095, blank=True, null=True, verbose_name="Текст")
    message_id = models.BigIntegerField(verbose_name="ID сообщении")
    data = models.JSONField(blank=True, null=True, verbose_name="Дата")

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

    def __str__(self):
        return str(self.message_id)


class TelegramCommand(BaseModel):
    command = models.CharField(max_length=15, unique=True, verbose_name="Название")
    description = models.CharField(max_length=63, verbose_name="Описание")
    content = HTMLField(verbose_name="Контент")
    cleaned_content = models.TextField(blank=True, null=True, editable=False)
    file = models.ImageField(upload_to="images/%Y/%m/%d", blank=True, null=True, verbose_name="Фото")
    file_id = models.CharField(max_length=255, blank=True, null=True, verbose_name="Файл ID")

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
    text = models.CharField(max_length=4095, verbose_name="Текст")
    text_list = ArrayField(models.CharField(max_length=31), blank=True, editable=False)
    content = HTMLField(verbose_name="Контент", help_text="Текст ответа")
    cleaned_content = models.TextField(blank=True, null=True, editable=False)
    count = models.BigIntegerField(default=0, editable=False)

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



