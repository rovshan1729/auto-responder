from django.db import models
from django.utils.timezone import now
from tinymce.models import HTMLField

from bot import utils
from responder.base import BaseModel
from responder.models import TelegramGroup


class Media(BaseModel):
    title = models.CharField(max_length=255, blank=True, null=True, verbose_name="Название")
    file = models.FileField(upload_to='telegram/%Y/%m/%d', verbose_name="Медиа файл")
    file_id = models.CharField(max_length=255, blank=True, null=True, verbose_name="Файл ID")
    file_type = models.CharField(max_length=15, blank=True, null=True, verbose_name="Тип файла")
    order = models.PositiveIntegerField(default=0, verbose_name="Порядок расположении")

    class Meta:
        verbose_name = "Медиа"
        verbose_name_plural = "Медиа"
        ordering = ('order',)

    def __str__(self):
        return self.title if self.title else f"Media: #{self.id}"


class BroadcastTemplate(BaseModel):
    title = models.CharField(max_length=255, blank=True, null=True, verbose_name="Название")
    content = HTMLField(blank=True, null=True, verbose_name="Контент")
    cleaned_content = models.TextField(blank=True, null=True, editable=False)
    medias = models.ManyToManyField(Media, blank=True, related_name='broadcast_templates',
                                    verbose_name="Прикрепляемые файлы")

    class Meta:
        verbose_name = "шаблон рассылки"
        verbose_name_plural = "Шаблоны рассылок"
        ordering = ('-created_at',)


    def save(self, *args, **kwargs):
        self.cleaned_content = utils.clean_from_html_v3(self.content)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Broadcast Template: #{self.id}"


class Broadcast(BaseModel):
    title = models.CharField(max_length=255, blank=True, null=True, verbose_name="Название")
    template = models.ForeignKey(
        BroadcastTemplate,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='broadcasts',
        verbose_name='Шаблон',
    )
    content = HTMLField(blank=True, null=True, verbose_name="Контент", help_text="Не нужно, если выбран шаблон")
    cleaned_content = models.TextField(blank=True, null=True, editable=False)

    medias = models.ManyToManyField(
        Media,
        blank=True,
        related_name='broadcasts',
        verbose_name="Прикрепляемые файлы",
        help_text="Не нужно, если выбран шаблон"
    )
    groups = models.ManyToManyField(
        TelegramGroup,
        blank=True,
        related_name='broadcast_templates',
        verbose_name="Телеграм группы",
    )
    task_id = models.IntegerField(blank=True, null=True, editable=False)
    scheduled_at = models.DateTimeField(default=now(), verbose_name="Расписание")
    percent = models.CharField(max_length=15, editable=False, verbose_name="Процент")
    check_groups = models.BooleanField(
        default=False,
        verbose_name="Выбрать все группы",
        help_text='Выбрать все группы, исключая “Archive”'
    )
    is_sent = models.BooleanField(default=False, editable=False, verbose_name="Отправлено")


    class Meta:
        verbose_name = "рассылку"
        verbose_name_plural = "Рассылка"
        ordering = ('-created_at',)

    def save(self, *args, **kwargs):
        if not self.scheduled_at:
            self.scheduled_at = now()

        if self.content:
            self.cleaned_content = utils.clean_from_html_v3(self.content)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title if self.title else f"Broadcast: #{self.id}"



class ButtonBase(BaseModel):
    text = models.CharField(max_length=31, help_text="Текст кнопки", verbose_name="Текст")
    url = models.URLField(verbose_name="Ссылка", help_text="Ссылка перенаправлении, например: https://www.example.com")
    order = models.PositiveSmallIntegerField(default=0, verbose_name="Порядок расположении")

    class Meta:
        verbose_name = ""
        verbose_name_plural = "Кнопки"
        ordering = ('order',)
        abstract = True


class TemplateButton(ButtonBase):
    template = models.ForeignKey('BroadcastTemplate', on_delete=models.CASCADE, related_name='template_buttons')

    def __str__(self):
        return str(self.text) or f"TemplateButton #{self.pk or 'new'}"

class BroadcastButton(ButtonBase):
    broadcast = models.ForeignKey('Broadcast', on_delete=models.CASCADE, related_name='broadcast_buttons')

    def __str__(self):
        return str(self.text) or f"BroadcastButton #{self.pk or 'new'}"
