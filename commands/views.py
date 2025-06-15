from django.db import models
from django.contrib.admin.sites import site
from django.contrib.admin.views.decorators import staff_member_required
from django.template.response import TemplateResponse
from django.utils.dateparse import parse_date
from responder.models import TelegramMessage, TelegramUser, Mask, FAQ


@staff_member_required
def admin_dashboard_view(request):
    app_list = site.get_app_list(request)

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    top_faq = FAQ.objects

    if start_date:
        top_faq = top_faq.filter(created_at__date__gte=parse_date(start_date))
    if end_date:
        top_faq = top_faq.filter(created_at__date__lte=parse_date(end_date))

    top_users = (
        TelegramUser.objects
        .exclude(username="GroupAnonymousBot")
        .annotate(message_count=models.Count("messages"))
        .order_by("-message_count")[:10]
    )

    top_faq = (
        top_faq.annotate(
            date=models.F("created_at__date"),
        ).order_by("-count")
    )

    top_questions = top_faq[:10]
    top_answers = top_faq.filter(answer__isnull=False)[:10]
    top_not_answers = top_faq.filter(answer__isnull=True)[:10]

    context = {
        'title': 'Аналитика',
        'available_apps': app_list,
        # 'user_daily_stats': json.dumps(list(user_daily_stats), cls=DjangoJSONEncoder),
        'top_users': top_users,
        'top_questions': list(top_questions),
        'top_answers': list(top_answers),
        'top_not_answers': list(top_not_answers),
    }
    return TemplateResponse(request, "admin/custom_dashboard.html", context)
