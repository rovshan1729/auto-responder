from django.contrib import admin
from django.contrib import messages
from django.db.models import Count
from django.template.loader import render_to_string
from django.utils.html import format_html
from django.utils.safestring import mark_safe
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

    def has_add_permission(self, request):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            count=Count("messages")
        ).order_by('-count').prefetch_related("users")


@admin.register(models.TelegramMessage)
class TelegramMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'group', 'user', 'text', 'message_id', 'is_marked', 'created_at',)
    list_display_links = ('id', 'group', 'user', 'message_id')
    list_filter = (
        'is_marked',
        'group__title',
        'group__username',
        'user__first_name',
        'user__username',
        ('group', admin.EmptyFieldListFilter),
    )
    inlines = [ReplyMessageInline, ]

    # def custom_button(self, obj):
    #     return format_html(
    #         '<button type="button" class="btn btn-primary btn-sm" data-toggle="modal" '
    #         'data-target="#modal-{}">Открыть форму</button>',
    #         obj.id
    #     )
    #
    # def get_urls(self):
    #     from django.urls import path
    #     urls = super().get_urls()
    #     custom_urls = [
    #         path(
    #             '<path:object_id>/custom_form/',
    #             self.admin_site.admin_view(self.custom_form_view),
    #             name='yourmodel-custom-form'
    #         ),
    #     ]
    #     return custom_urls + urls
    #
    # def custom_form_view(self, request, object_id):
    #     # Логика для обработки формы в модальном окне
    #     from django.http import JsonResponse
    #     from django.shortcuts import render
    #     from .forms import ReplyMessageForm
    #     reply_message = models.ReplyMessage.objects.filter(message_id=object_id).first()
    #     if request.method == 'POST':
    #         form = ReplyMessageForm(request.POST)
    #         if reply_message:
    #             form = ReplyMessageForm(request.POST, instance=reply_message)
    #         if form.is_valid():
    #             form.save()
    #             return JsonResponse({'success': True})
    #         return JsonResponse({'success': False, 'errors': form.errors})
    #     form = ReplyMessageForm()
    #     if reply_message:
    #         form = ReplyMessageForm(instance=reply_message)
    #
    #     context = {
    #         'form': form,
    #         'object_id': object_id,
    #         'opts': self.model._meta,
    #     }
    #     return render(request, 'admin/_responder/telegrammessage/custom_form_modal.html', context)

    def has_add_permission(self, request):
        return False

    # custom_button.short_description = "Действие"

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
