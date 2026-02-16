from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings

from commands.views import *

urlpatterns = [
    path('admin/analytics/', admin_dashboard_view, name='admin-analytics'),
    path('admin/', admin.site.urls),
    path('tinymce/', include('tinymce.urls')),
    path('send/<int:object_id>/', admin_send_reply_view, name='send-reply-view'),
    path(settings.WEBHOOK_PATH, telegram_webhook, name="telegram_webhook"),
]

if settings.DEBUG:
    from debug_toolbar.toolbar import debug_toolbar_urls

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += debug_toolbar_urls()
