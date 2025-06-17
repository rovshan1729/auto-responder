from django.contrib import admin
from django.contrib import messages
from django.db.models import Count
from solo.admin import SingletonModelAdmin

from responder import models
from bot.utils import methods


@admin.action(description="Установить командную меню бота")
def set_command_menu(modeladmin, request, queryset):
    commands = list(queryset.values("command", "description"))
    response = methods.set_my_commands(commands)
    if response.status_code == 200:
        # print(f"\n{response.json()}\n")
        modeladmin.message_user(request, "Команды бота успешно установлены!", level=messages.SUCCESS)
    else:
        modeladmin.message_user(request, "Не удалось установить команды бота!", level=messages.ERROR)


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


    def has_add_permission(self, request):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            count=Count("messages")
        ).order_by('-count').prefetch_related("users")


@admin.register(models.TelegramMessage)
class TelegramMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'message_id', 'group', 'user', 'text', 'created_at')
    list_display_links = ('id', 'message_id')
    list_filter = (
        'group__title',
        'group__username',
        'user__first_name',
        'user__username',
        ('group', admin.EmptyFieldListFilter),
    )

    def has_add_permission(self, request):
        return False


@admin.register(models.TelegramCommand)
class TelegramCommandAdmin(admin.ModelAdmin):
    list_display = ('id', 'command', 'created_at')
    list_display_links = ('id', 'command')
    actions = (set_command_menu,)


@admin.register(models.Mask)
class MaskAdmin(admin.ModelAdmin):
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
