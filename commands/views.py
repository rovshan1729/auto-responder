from django.db import models
from django.contrib.admin.sites import site
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Min, F
from django.template.response import TemplateResponse
from django.utils.dateparse import parse_date
from responder.models import TelegramMessage, TelegramUser, Mask, FAQ


@staff_member_required
def admin_dashboard_view(request):
    app_list = site.get_app_list(request)

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # top_faq = FAQ.objects
    top_questions =  TelegramMessage.objects
    top_answers = TelegramMessage.objects.filter(answer__isnull=False)
    top_not_answered = TelegramMessage.objects.filter(answer__isnull=True)

    if start_date:
        # top_faq = top_faq.filter(created_at__date__gte=parse_date(start_date))
        top_questions = top_questions.filter(created_at__date__gte=parse_date(start_date))
        top_answers = top_answers.filter(created_at__date__gte=parse_date(start_date))
        top_not_answered = top_not_answered.filter(created_at__date__gte=parse_date(start_date))
    if end_date:
        # top_faq = top_faq.filter(created_at__date__lte=parse_date(end_date))
        top_questions = top_questions.filter(created_at__date__lte=parse_date(end_date))
        top_answers = top_answers.filter(created_at__date__lte=parse_date(end_date))
        top_not_answered = top_not_answered.filter(created_at__date__lte=parse_date(end_date))

    top_users = (
        TelegramUser.objects
        .exclude(username="GroupAnonymousBot")
        .exclude(is_blocked=True)
        .annotate(message_count=models.Count("messages", distinct=True))
        .order_by("-message_count")[:20]
    )
    # Top questions
    top_questions = top_questions.values('text_list').annotate(
        count=Count('id'),
        min_id=Min('id')
    ).order_by('-count')[:20]

    ids = [g['min_id'] for g in top_questions]
    texts = TelegramMessage.objects.annotate(
        date=F("created_at__date")
    ).in_bulk(ids)

    top_questions_result = [
        {
            "text": texts[g['min_id']].text,
            "date": texts[g['min_id']].date,
            "count": g['count']
        } for g in top_questions
    ]

    # Top answers
    top_answers = top_answers.values('answer_list').annotate(
        count=Count('id'),
        min_id=Min('id')
    ).order_by('-count')[:20]

    aids = [a['min_id'] for a in top_answers]
    answers = TelegramMessage.objects.annotate(
        date=F("created_at__date")
    ).in_bulk(aids)

    top_answers_result = [
        {
            "text": answers[a['min_id']].answer,
            "date": answers[a['min_id']].date,
            "count": a['count']
        } for a in top_answers
    ]

    # Top not answered questions
    top_not_answered = top_not_answered.values('text_list').annotate(
        count=Count('id'),
        min_id=Min('id')
    ).order_by('-count')[:20]

    not_ids = [g['min_id'] for g in top_not_answered]
    not_ans_texts = TelegramMessage.objects.annotate(
        date=F("created_at__date")
    ).in_bulk(not_ids)

    top_not_answered_result = [
        {
            "text": not_ans_texts[g['min_id']].text,
            "date": not_ans_texts[g['min_id']].date,
            "count": g['count'],
        } for g in top_not_answered
    ]

    # top_faq = (
    #     top_faq.annotate(
    #         date=models.F("created_at__date"),
    #     ).order_by("-count")
    # )
    #
    # top_questions = top_faq[:20]
    # top_answers = top_faq.filter(answer__isnull=False)[:20]
    # top_not_answers = top_faq.filter(answer__isnull=True)[:20]

    context = {
        'title': 'Аналитика',
        'available_apps': app_list,
        # 'user_daily_stats': json.dumps(list(user_daily_stats), cls=DjangoJSONEncoder),
        'top_users': top_users,
        # 'top_questions': list(top_questions),
        'top_questions': top_questions_result,
        # 'top_answers': list(top_answers),
        'top_answers': top_answers_result,
        # 'top_not_answers': list(top_not_answers),
        'top_not_answers': top_not_answered_result,
    }
    return TemplateResponse(request, "admin/custom_dashboard.html", context)
