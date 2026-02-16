import logging

from django.contrib import messages

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import admin
from django.db.models import Count
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_date

from bot.webhook import webhook
from responder.models import TelegramMessage, TelegramUser


@staff_member_required
def admin_send_reply_view(request,  object_id):
    print(f"Worked custom form view")
    messages.success(request, "Worked send reply message")
    # reply_message = ReplyMessage.objects.filter(message__id=object_id).first()
    # print(f"ReplyMessage: {reply_message}")
    # if request.method == 'POST':
    #     form = ReplyMessageForm(request.POST)
    #
    #     if reply_message is not None:
    #         form = ReplyMessageForm(request.POST, instance=reply_message)
    #
    #     if form.is_valid():
    #         print("Form is valid")
    #         reply_message = form.save(commit=False)
    #         reply_message.message_id = object_id
    #         if not reply_message.cleaned_text:
    #             reply_message.cleaned_text = utils.clean_from_html_v3(reply_message.text)
    #         reply_message.save()
    #         messages.success(request, "Успешно отправлено сообщение.")
    #     else:
    #         print(f"Form is invalid")
    #         messages.error(request, "Ошибка при отравки.")
    # else:
    #     print(f"{request.method = }")
    return redirect("admin:index")
    # return redirect(reverse('admin:responder_telegrammessage_changelist'))


# @staff_member_required
# def admin_dashboard_view(request):
#     app_list = site.get_app_list(request)
#
#     start_date = request.GET.get('start_date')
#     end_date = request.GET.get('end_date')
#
#     # top_faq = FAQ.objects
#     top_questions =  TelegramMessage.objects.filter(user__is_blocked=False)
#     top_answers = TelegramMessage.objects.filter(answer__isnull=False)
#     top_not_answered = TelegramMessage.objects.filter(answer__isnull=True, user__is_blocked=False)
#     top_users = TelegramUser.objects
#
#     if start_date:
#         # top_faq = top_faq.filter(created_at__date__gte=parse_date(start_date))
#         top_questions = top_questions.filter(created_at__date__gte=parse_date(start_date))
#         top_answers = top_answers.filter(created_at__date__gte=parse_date(start_date))
#         top_not_answered = top_not_answered.filter(created_at__date__gte=parse_date(start_date))
#         top_users = top_users.filter(messages__created_at__date__gte=parse_date(start_date))
#     if end_date:
#         # top_faq = top_faq.filter(created_at__date__lte=parse_date(end_date))
#         top_questions = top_questions.filter(created_at__date__lte=parse_date(end_date))
#         top_answers = top_answers.filter(created_at__date__lte=parse_date(end_date))
#         top_not_answered = top_not_answered.filter(created_at__date__lte=parse_date(end_date))
#         top_users = top_users.filter(messages__created_at__date__lte=parse_date(end_date))
#
#     top_users = (
#         top_users
#         .exclude(username="GroupAnonymousBot")
#         .exclude(is_blocked=True)
#         .annotate(message_count=models.Count("messages", distinct=True))
#         .order_by("-message_count")[:20]
#     )
#     # Top questions
#     top_questions = top_questions.values('text_list').annotate(
#         count=Count('id'),
#         min_id=Min('id')
#     ).order_by('-count')[:20]
#
#     ids = [g['min_id'] for g in top_questions]
#     texts = TelegramMessage.objects.annotate(
#         date=F("created_at__date")
#     ).in_bulk(ids)
#
#     top_questions_result = [
#         {
#             "text": texts[g['min_id']].text,
#             "date": texts[g['min_id']].date,
#             "count": g['count']
#         } for g in top_questions
#     ]
#
#     # Top answers
#     top_answers = top_answers.values('answer_list').annotate(
#         count=Count('id'),
#         min_id=Min('id')
#     ).order_by('-count')[:20]
#
#     aids = [a['min_id'] for a in top_answers]
#     answers = TelegramMessage.objects.annotate(
#         date=F("created_at__date")
#     ).in_bulk(aids)
#
#     top_answers_result = [
#         {
#             "text": answers[a['min_id']].answer,
#             "date": answers[a['min_id']].date,
#             "count": a['count']
#         } for a in top_answers
#     ]
#
#     # Top not answered questions
#     top_not_answered = top_not_answered.values('text_list').annotate(
#         count=Count('id'),
#         min_id=Min('id')
#     ).order_by('-count')[:20]
#
#     not_ids = [g['min_id'] for g in top_not_answered]
#     not_ans_texts = TelegramMessage.objects.annotate(
#         date=F("created_at__date")
#     ).in_bulk(not_ids)
#
#     top_not_answered_result = [
#         {
#             "text": not_ans_texts[g['min_id']].text,
#             "date": not_ans_texts[g['min_id']].date,
#             "count": g['count'],
#         } for g in top_not_answered
#     ]
#
#     context = {
#         'title': 'Аналитика',
#         'available_apps': app_list,
#         'top_users': top_users,
#         'top_questions': top_questions_result,
#         'top_answers': top_answers_result,
#         'top_not_answers': top_not_answered_result,
#     }
#     return TemplateResponse(request, "admin/custom_dashboard.html", context)


# @staff_member_required
# def admin_dashboard_view(request):
#
#     start_date = request.GET.get("start_date")
#     end_date = request.GET.get("end_date")
#
#     top_questions = TelegramMessage.objects.filter(user__is_blocked=False)
#     top_answers = TelegramMessage.objects.filter(answer__isnull=False)
#     top_not_answered = TelegramMessage.objects.filter(
#         answer__isnull=True,
#         user__is_blocked=False
#     )
#     top_users = TelegramUser.objects
#
#     if start_date:
#         d = parse_date(start_date)
#         top_questions = top_questions.filter(created_at__date__gte=d)
#         top_answers = top_answers.filter(created_at__date__gte=d)
#         top_not_answered = top_not_answered.filter(created_at__date__gte=d)
#         top_users = top_users.filter(messages__created_at__date__gte=d)
#
#     if end_date:
#         d = parse_date(end_date)
#         top_questions = top_questions.filter(created_at__date__lte=d)
#         top_answers = top_answers.filter(created_at__date__lte=d)
#         top_not_answered = top_not_answered.filter(created_at__date__lte=d)
#         top_users = top_users.filter(messages__created_at__date__lte=d)
#
#     top_users = (
#         top_users
#         .exclude(username="GroupAnonymousBot")
#         .exclude(is_blocked=True)
#         .annotate(message_count=Count("messages", distinct=True))
#         .order_by("-message_count")[:20]
#     )
#
#     context = dict(
#         admin.site.each_context(request),
#         title="Аналитика",
#         top_users=top_users,
#         top_questions=top_questions,
#         top_answers=top_answers,
#         top_not_answers=top_not_answered,
#     )
#
#     return TemplateResponse(
#         request,
#         "admin/custom_dashboard.html",
#         context,
#     )


# @csrf_exempt
# async def telegram_webhook(request: HttpRequest):
#     if request.method != 'POST':
#         return HttpResponse(status=405)
#     try:
#         body = request.body.decode("utf-8")
#         await webhook.process_body(body)  # Await напрямую
#         return HttpResponse(status=200)
#     except Exception as e:
#         logging.error(f"Webhook error: {e}")
#         return HttpResponse(status=200)


@staff_member_required
def admin_dashboard_view(request):
    """
    Представление аналитической панели администратора

    Показывает:
    - Топ активных пользователей по количеству сообщений
    - Последние вопросы
    - Последние ответы
    - Вопросы без ответов

    Фильтрация по датам через GET параметры:
    - start_date: дата начала периода (YYYY-MM-DD)
    - end_date: дата окончания периода (YYYY-MM-DD)
    """

    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    # Базовые querysets
    all_messages = TelegramMessage.objects.all()
    all_users = TelegramUser.objects.all()

    # Применяем фильтры по датам
    if start_date:
        d = parse_date(start_date)
        if d:
            all_messages = all_messages.filter(created_at__date__gte=d)
            all_users = all_users.filter(messages__created_at__date__gte=d)

    if end_date:
        d = parse_date(end_date)
        if d:
            all_messages = all_messages.filter(created_at__date__lte=d)
            all_users = all_users.filter(messages__created_at__date__lte=d)

    # Топ пользователей по активности
    top_users = (
        all_users
        .exclude(username="GroupAnonymousBot")
        .exclude(is_blocked=True)
        .annotate(message_count=Count("messages", distinct=True))
        .filter(message_count__gt=0)
        .order_by("-message_count")[:20]
    )

    # Все вопросы (сообщения от незаблокированных пользователей)
    top_questions = (
        all_messages
        .filter(user__is_blocked=False)
        .select_related('user')
        .order_by('-created_at')
    )

    # Вопросы с ответами
    top_answers = (
        all_messages
        .filter(answer__isnull=False)
        .select_related('user')
        .order_by('-created_at')
    )

    # Вопросы без ответов (требуют внимания)
    top_not_answers = (
        all_messages
        .filter(
            answer__isnull=True,
            user__is_blocked=False
        )
        .select_related('user')
        .order_by('-created_at')
    )

    context = dict(
        admin.site.each_context(request),
        title="Аналитика",
        top_users=top_users,
        top_questions=top_questions,
        top_answers=top_answers,
        top_not_answers=top_not_answers,
    )

    return TemplateResponse(
        request,
        "admin/custom_dashboard.html",
        context,
    )


@csrf_exempt
async def telegram_webhook(request):

    if request.method != "POST":
        return HttpResponse(status=405)

    try:
        body_bytes = request.body  # ❗ БЕЗ await
        body = body_bytes.decode("utf-8")

        await webhook.process_body(body)

        return HttpResponse(status=200)

    except Exception:
        logging.exception("Webhook error")
        return HttpResponse(status=200)


