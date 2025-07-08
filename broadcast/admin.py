from django.shortcuts import redirect
from django.urls import path
from django.contrib import admin
from django.contrib import messages

from . import models


class TButtonInline(admin.TabularInline):
    model = models.TemplateButton
    extra = 0


class BButtonInline(admin.TabularInline):
    model = models.BroadcastButton
    extra = 0


@admin.register(models.Media)
class MediaAdmin(admin.ModelAdmin):
    list_display = ('id', 'file_id', 'order')


@admin.register(models.BroadcastTemplate)
class BroadcastTemplateAdmin(admin.ModelAdmin):
    inlines = (TButtonInline,)


@admin.register(models.Broadcast)
class BroadcastAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'percent', 'is_sent', 'created_at')
    fields = ('title', 'template', 'groups', 'check_groups', 'medias', 'content', 'scheduled_at')
    inlines = (BButtonInline,)

    def response_add(self, request, obj, post_url_continue=None):
        if "_save_now" in request.POST:
            self.message_user(request, "Успешно отправлено!", level=messages.SUCCESS)
            return self.response_post_save_add(request, obj)
        return super().response_add(request, obj, post_url_continue)
