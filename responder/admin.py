from django.contrib import admin
from django.contrib import messages
from django.db.models import Count
from django.template.loader import render_to_string
from django.utils.html import format_html

from unfold import admin as unfold_admin
from unfold.decorators import action as unfold_action

from solo.admin import SingletonModelAdmin

from bot import utils
from bot.utils import methods
from responder import models, mixins
from responder.forms import ReplyMessageForm, MaskModelForm

admin.site.register(models.Profile)
admin.site.register(models.WorkerData)
admin.site.register(models.Merchant)
admin.site.register(models.Country)
admin.site.register(models.StaticText)


class VerificationAdminFieldInline(admin.TabularInline):
    model = models.VerificationAdminField
    extra = 1
    fields = ("label", "field_type", "value")


@admin.register(models.AllVerification)
class AllVerificationAdmin(admin.ModelAdmin, mixins.VerificationAdminMixin):
    list_display = (
        "fullname",
        "phone_number",
        "status",
        "country",
        "is_blacklisted"
    )

    readonly_fields = (
        "main_passport_preview",
        "registration_passport_preview",
        "additional_passport_preview",
        "round_video_preview",
    )

    fieldsets = (
        ("User info", {
            "fields": ("chat_id", "fullname", "username", "live_address", "phone_number", "add_phone", "email",
                       "experience", "token", "team_lead", "recommend_user", "status", "geo", "worked_platform",
                       "recommendation_user_contact", "additionally", "commentary", "country", "expires_at",
                       "is_blacklisted")
        }),
        ("Documents", {
            "fields": (
                "main_page_passport",
                "main_passport_preview",
                "registration_page_passport",
                "registration_passport_preview",
                "additional_information_passport",
                "additional_passport_preview",
                "round_video",
                "round_video_preview",
            )
        }),
    )

    inlines = [VerificationAdminFieldInline]


@admin.register(models.CurrentVerification)
class CurrentVerificationAdmin(admin.ModelAdmin, mixins.VerificationAdminMixin):
    list_display = (
        "fullname",
        "phone_number",
        "status",
        "country",
        "is_blacklisted"
    )

    readonly_fields = (
        "main_passport_preview",
        "registration_passport_preview",
        "additional_passport_preview",
        "round_video_preview",
    )

    fieldsets = (
        ("User info", {
            "fields": ("chat_id", "fullname", "username", "live_address", "phone_number", "add_phone", "email",
                       "experience", "token", "team_lead", "recommend_user", "status", "geo", "worked_platform",
                       "recommendation_user_contact", "additionally", "commentary", "country", "expires_at",
                       "is_blacklisted")
        }),
        ("Documents", {
            "fields": (
                "main_page_passport",
                "main_passport_preview",
                "registration_page_passport",
                "registration_passport_preview",
                "additional_information_passport",
                "additional_passport_preview",
                "round_video",
                "round_video_preview",
            )
        }),
    )

    inlines = [VerificationAdminFieldInline]


@admin.register(models.ArchivedVerification)
class ArchivedVerificationAdmin(admin.ModelAdmin, mixins.VerificationAdminMixin):
    list_display = (
        "fullname",
        "phone_number",
        "status",
        "country",
        "is_blacklisted"
    )

    readonly_fields = (
        "main_passport_preview",
        "registration_passport_preview",
        "additional_passport_preview",
        "round_video_preview",
    )

    fieldsets = (
        ("User info", {
            "fields": ("chat_id", "fullname", "username", "live_address", "phone_number", "add_phone", "email",
                       "experience", "token", "team_lead", "recommend_user", "status", "geo", "worked_platform",
                       "recommendation_user_contact", "additionally", "commentary", "country", "expires_at",
                       "is_blacklisted")
        }),
        ("Documents", {
            "fields": (
                "main_page_passport",
                "main_passport_preview",
                "registration_page_passport",
                "registration_passport_preview",
                "additional_information_passport",
                "additional_passport_preview",
                "round_video",
                "round_video_preview",
            )
        }),
    )

    inlines = [VerificationAdminFieldInline]


@unfold_action(description="Установить командную меню бота")
def set_command_menu(modeladmin, request, queryset):
    commands = list(queryset.values("command", "description"))
    response = methods.set_my_commands(commands)
    if response.status_code == 200:
        # print(f"\n{response.json()}\n")
        modeladmin.message_user(request, "Команды бота успешно установлены!", level=messages.SUCCESS)
    else:
        modeladmin.message_user(request, "Не удалось установить команды бота!", level=messages.ERROR)


class ReplyMessageInline(unfold_admin.TabularInline):
    model = models.ReplyMessage
    extra = 0

    fieldsets = (
        (None, {
            "fields": (
                ("message", "is_retry",),
                ("text", "cleaned_text",),
            )
        }),
    )


class TelegramUserInline(unfold_admin.TabularInline):
    model = models.TelegramUser
    filter_horizontal = ("groups",)
    extra = 0

    fieldsets = (
        (
            None, {
            "fields": (
                ("telegram_id", "username", "is_blocked"),
                ("first_name", "last_name"),
                ("groups",),
            ),
        }),
    )


class TelegramMessageInline(unfold_admin.StackedInline):
    model = models.TelegramMessage
    # fields = ('text', 'message_id', 'group')
    extra = 0

    fieldsets = (
        (None, {
            "fields": (
                ("group", "user"),
                ("text", "answer"),
                ("text_list", "answer_list"),
                ("message_id", "is_marked"),
            )
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("group", 'user')


@admin.register(models.TelegramUser)
class TelegramUserAdmin(unfold_admin.ModelAdmin):
    list_display = ('id', 'telegram_id', 'username', 'first_name', 'count', 'is_blocked', 'created_at')
    list_display_links = ('id', 'telegram_id')
    list_editable = ('is_blocked',)
    list_filter = ('is_blocked',)
    search_fields = ('telegram_id', 'username', 'first_name',)

    inlines = [TelegramMessageInline, ]

    fieldsets = (
        (
            None, {
            "fields": (
                ("telegram_id", "username", "is_blocked"),
                ("first_name", "last_name"),
                ("groups",),
            ),
        }),
    )

    @unfold_admin.display(description="Количество сообщении")
    def count(self, obj):
        return obj.messages.count()

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            count=Count("messages")
        ).order_by('-count')


@admin.register(models.TelegramGroup)
class TelegramGroupAdmin(unfold_admin.ModelAdmin):
    list_display = ('id', 'telegram_id', 'username', 'title', 'count', 'created_at')
    list_display_links = ('id', 'telegram_id')
    list_filter = ('status',)
    search_fields = ("telegram_id", 'username', 'title')

    # inlines = (TelegramUserInline,)

    fieldsets = (
        (None, {
            "fields": (
                ("telegram_id", "username", "is_active"),
                ("title", 'status')
            )
        }),
    )

    @unfold_admin.display(description="Количество сообщении")
    def count(self, obj):
        return obj.messages.count()

    # def has_add_permission(self, request):
    #     return False

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            count=Count("messages")
        ).order_by('-count').prefetch_related("users")


@admin.register(models.TelegramMessage)
class TelegramMessageAdmin(unfold_admin.ModelAdmin):
    list_display = ('id', 'group', 'user', 'text', 'message_id', 'is_marked', 'created_at', "custom_btn")
    list_display_links = ('id', 'group', 'user', 'message_id')
    readonly_fields = ('text_list',)
    # fields = ('group', 'user', 'text', 'text_list', 'message_id', 'is_marked', 'data')
    list_filter = (
        'is_marked',
        'group__title',
        'group__username',
        'user__first_name',
        'user__username',
        ('group', admin.EmptyFieldListFilter),
    )
    inlines = [ReplyMessageInline, ]

    fieldsets = (
        (None, {
            "fields": (
                ("group", "user"),
                ("text", "answer"),
                ("text_list", "answer_list"),
                ("message_id", "is_marked"),
            )
        }),
    )

    @unfold_admin.display(description="Действие")
    def custom_btn(self, obj):
        html = render_to_string(
            'admin/responder/telegrammessage/custom_button.html',
            {
                'obj': obj,
                'disabled': obj.answer is not None,
            }
        )
        return format_html(html)

    def changelist_view(self, request, extra_context=None):

        message_id = request.POST.get("message_id")
        if message_id:
            reply_message = models.ReplyMessage.objects.filter(message_id=message_id).first()

            obj_form = ReplyMessageForm(request.POST)
            if reply_message:
                obj_form = ReplyMessageForm(request.POST, instance=reply_message)

            if obj_form.is_valid():
                obj = obj_form.save(commit=False)
                obj.message_id = message_id
                obj.save()
                messages.success(request, "Сообщение успешно отправлено")
            else:
                messages.error(request, "Ошибка  при отправки сообщении")

        if extra_context is None:
            extra_context = {}

        form = ReplyMessageForm()
        extra_context['custom_form'] = form

        return super().changelist_view(request, extra_context)

    def has_add_permission(self, request):
        return False


@admin.register(models.TelegramCommand)
class TelegramCommandAdmin(unfold_admin.ModelAdmin):
    list_display = ('id', 'command', 'created_at')
    list_display_links = ('id', 'command')
    actions = (set_command_menu,)

    fieldsets = (
        (None, {
            "fields": (
                ("command", "description"),
                ("content", "cleaned_content"),
                ("file", "file_id"),
            )
        }),
    )


@admin.register(models.Mask)
class MaskAdmin(unfold_admin.ModelAdmin):
    form = MaskModelForm
    list_display = ('id', 'text', 'created_at')
    list_display_links = ('id', 'text')
    search_fields = ("text",)

    fieldsets = (
        (None, {
            "fields": (
                ("groups", "text_list"),
                ("text", "content"),
                ("cleaned_content", "count")
            )
        }),
    )


@admin.register(models.FAQ)
class FAQAdmin(unfold_admin.ModelAdmin):
    list_display = ('id', 'question', 'answer', 'count', 'created_at')
    list_display_links = ()
    list_filter = (('answer', admin.EmptyFieldListFilter),)

    fieldsets = (
        (None, {
            "fields": (
                ("question", "answer"),
                ("count",)
            )
        }),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(models.Data)
class DataAdmin(unfold_admin.ModelAdmin):
    readonly_fields = ('channel_id',)

    def has_add_permission(self, request):
        return False
