from django.contrib import admin
from django.contrib import messages

from unfold.admin import ModelAdmin, TabularInline

from . import models
from .forms import BroadcastModelForm


class TButtonInline(TabularInline):
    model = models.TemplateButton
    extra = 0


class BButtonInline(TabularInline):
    model = models.BroadcastButton
    extra = 0


@admin.register(models.Media)
class MediaAdmin(ModelAdmin):
    list_display = ('id', 'file_id', 'order')

    fieldsets = (
        (None, {
            "fields": (
                ("title", "file_type", "order"),
                ("file", "file_id"),
            )
        }),
    )


@admin.register(models.BroadcastTemplate)
class BroadcastTemplateAdmin(ModelAdmin):

    filter_horizontal = ("medias",)
    inlines = (TButtonInline,)

    fieldsets = (
        (None, {
            "fields": (
                ("title",),
                ("content", "cleaned_content"),
                ("medias",)
            )
        }),
    )


@admin.register(models.Broadcast)
class BroadcastAdmin(ModelAdmin):
    form = BroadcastModelForm
    list_display = ('id', 'title', 'percent', 'is_sent', 'created_at')
    # fields = ('title', 'template', 'groups', 'medias', 'content', 'scheduled_at')
    inlines = (BButtonInline,)


    fieldsets = (
        (None, {
            "fields": (
                ("title", "template"),
                ("content", "cleaned_content"),
                ("medias",),
                ("groups",),
                ("scheduled_at", "task_id"),
                ("percent", "is_sent"),
            )
        }),
    )


    def response_add(self, request, obj, post_url_continue=None):
        if "_save_now" in request.POST:
            self.message_user(request, "Успешно отправлено!", level=messages.SUCCESS)
            return self.response_post_save_add(request, obj)
        return super().response_add(request, obj, post_url_continue)
