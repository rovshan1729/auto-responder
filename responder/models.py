from django.db import models
from django.urls import reverse
from django.contrib.postgres.fields import ArrayField

from tinymce.models import HTMLField
from solo.models import SingletonModel

from .base import BaseModel
from .choices import ChatMemberStatus, GroupChoice, VerificationStatusChoice, AdminFieldType, UserRole, DisputeStatus
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

    class Meta:
        verbose_name = "Страна"
        verbose_name_plural = "Страны"

    def __str__(self):
        return self.title


class StaticText(BaseModel):
    code = models.CharField(max_length=256, unique=True, verbose_name="Код")
    text = models.TextField(verbose_name="Текст")

    class Meta:
        verbose_name = "Статический текст"
        verbose_name_plural = "Статические тексты"

    def __str__(self):
        return f"{self.code} - {self.text}"


class Verification(BaseModel):
    chat_id = models.CharField(max_length=128, verbose_name="Chat ID")

    fullname = models.CharField(max_length=255, null=True, blank=True, verbose_name="ФИО")
    username = models.CharField(max_length=255, null=True, blank=True, verbose_name="Имя пользователя")

    live_address = models.TextField(null=True, blank=True, verbose_name="Адрес проживания")

    phone_number = models.CharField(max_length=20, null=True, blank=True, verbose_name="Номер телефона")
    add_phone = models.CharField(max_length=20, null=True, blank=True, verbose_name="Дополнительный телефон")

    email = models.EmailField(verbose_name="Email", null=True, blank=True)
    experience = models.CharField(max_length=50, null=True, blank=True, verbose_name="Опыт работы")

    token = models.CharField(max_length=255, null=True, blank=True, verbose_name="Токен")

    team_lead = models.CharField(max_length=100, null=True, blank=True, verbose_name="Тимлид")
    recommend_user = models.CharField(max_length=100, null=True, blank=True, verbose_name="Рекомендовал")

    status = models.CharField(
        max_length=50,
        choices=VerificationStatusChoice.choices,
        verbose_name="Статус верификации"
    )

    geo = models.TextField(null=True, blank=True, verbose_name="Геолокация")
    worked_platform = models.TextField(null=True, blank=True, verbose_name="Рабочие платформы")
    recommendation_user_contact = models.TextField(null=True, blank=True, verbose_name="Контакт рекомендателя")
    additionally = models.TextField(null=True, blank=True, verbose_name="Дополнительная информация")
    commentary = models.TextField(null=True, blank=True, verbose_name="Комментарий администратора")

    main_page_passport = models.ImageField(upload_to="verification/", null=True, blank=True,
                                           verbose_name="Паспорт (главная страница)")
    registration_page_passport = models.ImageField(upload_to="verification/", null=True, blank=True,
                                                   verbose_name="Паспорт (страница регистрации)")
    additional_information_passport = models.ImageField(upload_to="verification/", null=True, blank=True,
                                                        verbose_name="Паспорт (дополнительная информация)")
    round_video = models.FileField(upload_to="verification/", null=True, blank=True, verbose_name="Видео-круг")

    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE, null=True, blank=True, verbose_name="Страна"
    )
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="Срок действия")
    is_blacklisted = models.BooleanField(default=False, verbose_name="В черном списке")

    class Meta:
        verbose_name = "Верификация"
        verbose_name_plural = "Верификации"

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


class Profile(BaseModel):
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name="profile",
                             verbose_name="Пользователь")
    role = models.CharField(max_length=64, choices=UserRole.choices, default=UserRole.USER, verbose_name="Роль")

    class Meta:
        verbose_name = "Профиль"
        verbose_name_plural = "Профили"


class WorkerData(BaseModel):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="profile", verbose_name="Сотрудник")
    start_work_time = models.DateTimeField(verbose_name="Время начала смены")
    finish_work_time = models.DateTimeField(null=True, blank=True, verbose_name="Время окончания смены")

    class Meta:
        verbose_name = "Смена сотрудника"
        verbose_name_plural = "Смены сотрудников"

    def __str__(self):
        return f"{self.profile.user} | {self.start_work_time}"


class Merchant(BaseModel):
    title = models.CharField(max_length=512, verbose_name="Название мерчанта")

    class Meta:
        verbose_name = "Мерчант"
        verbose_name_plural = "Мерчанты"

    def __str__(self):
        return f"{self.title}"


class WorkerShiftReport(BaseModel):
    worker_data = models.OneToOneField(WorkerData, on_delete=models.CASCADE, related_name="report",
                                       verbose_name="Смена")
    is_submitted = models.BooleanField(default=False, verbose_name="Отчет отправлен")
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата отправки отчета")

    comment = models.TextField(null=True, blank=True, verbose_name="Комментарий / проблема")

    class Meta:
        verbose_name = "Отчет по смене"
        verbose_name_plural = "Отчеты по сменам"

    def __str__(self):
        return f"Report #{self.id} | {self.worker_data.profile.user}"


class WorkerDispute(BaseModel):
    report = models.ForeignKey(WorkerShiftReport, on_delete=models.CASCADE, related_name="disputes",
                               verbose_name="Отчет по смене")
    merchant = models.ForeignKey(Merchant, on_delete=models.PROTECT, related_name="dispute", verbose_name="Мерчант")

    count = models.IntegerField(default=0, verbose_name="Количество диспутов")

    status = models.CharField(max_length=32, choices=DisputeStatus.choices, default=DisputeStatus.NEW,
                              verbose_name="Статус диспута")

    class Meta:
        verbose_name = "Диспут"
        verbose_name_plural = "Диспуты"

    def __str__(self):
        return f"{self.report.worker_data.profile.user} | {self.merchant.title} | {self.count} | {self.status}"


class WorkerIssue(BaseModel):
    report = models.ForeignKey(
        WorkerShiftReport,
        on_delete=models.CASCADE,
        related_name="issues",
        verbose_name="Отчет по смене"
    )

    merchant = models.ForeignKey(
        Merchant,
        on_delete=models.PROTECT,
        related_name="issues",
        verbose_name="Мерчант"
    )

    text = models.TextField(verbose_name="Описание проблемы")

    class Meta:
        verbose_name = "Проблема по смене"
        verbose_name_plural = "Проблемы по сменам"

    def __str__(self):
        return f"{self.report.worker_data.profile.user} | {self.merchant.title}"


class Problem(BaseModel):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="problems", verbose_name="Сотрудник")
    text = models.TextField(verbose_name="Описание проблемы")

    class Meta:
        verbose_name = "Проблема сотрудника"
        verbose_name_plural = "Проблемы сотрудников"

    def __str__(self):
        return str(self.profile.user)


class BlackList(BaseModel):
    groups = models.ForeignKey(TelegramGroup, on_delete=models.CASCADE, verbose_name="Название группы")
    verification = models.ManyToManyField(Verification, related_name="blacklists",
                                          verbose_name="Найденные профили")

    class Meta:
        verbose_name = "Черные списки"
        verbose_name_plural = "Черный список"

    def __str__(self):
        return f"{self.groups} | {self.verification}"