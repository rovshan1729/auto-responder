from django.contrib import admin
from django.contrib import messages
from django.db.models import Count
from django.template.loader import render_to_string
from django.utils.html import format_html

from solo.admin import SingletonModelAdmin

from bot import utils
from bot.utils import methods
from responder import models, mixins
from responder.forms import ReplyMessageForm, MaskModelForm

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
                       "recommendation_user_contact", "additionally", "commentary", "country", "expires_at")
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
                       "recommendation_user_contact", "additionally", "commentary", "country", "expires_at")
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
                       "recommendation_user_contact", "additionally", "commentary", "country", "expires_at")
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


@admin.action(description="Установить командную меню бота")
def set_command_menu(modeladmin, request, queryset):
    commands = list(queryset.values("command", "description"))
    response = methods.set_my_commands(commands)
    if response.status_code == 200:
        # print(f"\n{response.json()}\n")
        modeladmin.message_user(request, "Команды бота успешно установлены!", level=messages.SUCCESS)
    else:
        modeladmin.message_user(request, "Не удалось установить команды бота!", level=messages.ERROR)


class ReplyMessageInline(admin.TabularInline):
    model = models.ReplyMessage
    extra = 0


class TelegramUserInline(admin.TabularInline):
    model = models.TelegramUser
    extra = 0


class TelegramMessageInline(admin.StackedInline):
    model = models.TelegramMessage
    fields = ('text', 'message_id', 'group')
    extra = 0

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("group", 'user')


@admin.register(models.TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'telegram_id', 'username', 'first_name', 'count', 'is_blocked', 'created_at')
    list_display_links = ('id', 'telegram_id')
    list_editable = ('is_blocked',)
    list_filter = ('is_blocked',)
    search_fields = ('telegram_id', 'username', 'first_name',)

    inlines = [TelegramMessageInline, ]

    @admin.display(description="Количество сообщении")
    def count(self, obj):
        return obj.messages.count()

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            count=Count("messages")
        ).order_by('-count')


@admin.register(models.TelegramGroup)
class TelegramGroupAdmin(admin.ModelAdmin):
    list_display = ('id', 'telegram_id', 'username', 'title', 'count', 'created_at')
    list_display_links = ('id', 'telegram_id')
    list_filter = ('status',)
    search_fields = ("telegram_id", 'username', 'title')

    # inlines = (TelegramUserInline,)

    @admin.display(description="Количество сообщении")
    def count(self, obj):
        return obj.messages.count()

    # def has_add_permission(self, request):
    #     return False

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            count=Count("messages")
        ).order_by('-count').prefetch_related("users")


@admin.register(models.TelegramMessage)
class TelegramMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'group', 'user', 'text', 'message_id', 'is_marked', 'created_at', "custom_btn")
    list_display_links = ('id', 'group', 'user', 'message_id')
    readonly_fields = ('text_list',)
    fields = ('group', 'user', 'text', 'text_list', 'message_id', 'is_marked', 'data')
    list_filter = (
        'is_marked',
        'group__title',
        'group__username',
        'user__first_name',
        'user__username',
        ('group', admin.EmptyFieldListFilter),
    )
    inlines = [ReplyMessageInline, ]

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

    custom_btn.short_description = "Действие"

    # class Media:
    #     js = (
    #         'https://code.jquery.com/jquery-3.6.0.min.js',
    #         'https://cdn.jsdelivr.net/npm/bootstrap@4.5/dist/js/bootstrap.bundle.min.js',
    #     )
    #     css = {
    #         'all': (
    #             'https://cdn.jsdelivr.net/npm/bootstrap@4.5/dist/css/bootstrap.min.css',
    #         )
    #     }


@admin.register(models.TelegramCommand)
class TelegramCommandAdmin(admin.ModelAdmin):
    list_display = ('id', 'command', 'created_at')
    list_display_links = ('id', 'command')
    actions = (set_command_menu,)


@admin.register(models.Mask)
class MaskAdmin(admin.ModelAdmin):
    form = MaskModelForm
    list_display = ('id', 'text', 'created_at')
    list_display_links = ('id', 'text')
    search_fields = ("text",)


@admin.register(models.FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'answer', 'count', 'created_at')
    list_display_links = ()
    list_filter = (
        ('answer', admin.EmptyFieldListFilter),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(models.Data)
class DataAdmin(SingletonModelAdmin):
    readonly_fields = ('channel_id',)
