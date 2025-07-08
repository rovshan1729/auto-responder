
from celery import shared_task
from broadcast import models as broadcast_models
from responder.models import TelegramGroup

from bot.utils import methods


@shared_task
def send_broadcast(broadcast_id: int):
    counter = 0
    broadcast = broadcast_models.Broadcast.objects.filter(
        id=broadcast_id
    ).select_related(
        "template"
    ).prefetch_related(
        "medias", "groups", "template__medias"
    ).first()

    if broadcast is None:
        return

    if broadcast.check_groups:
        groups = TelegramGroup.objects.all().exclude(
            title__icontains="Archive"
        ).values_list('telegram_id', flat=True)
    else:
        groups = broadcast.groups.all().exclude(
            title__icontains="Archive"
        ).values_list("telegram_id", flat=True)

    if not groups:
        groups = TelegramGroup.objects.all().exclude(
            title__icontains="Archive"
        ).values_list("telegram_id", flat=True)

    if broadcast.template_id:
        content = broadcast.template.cleaned_content
        file_ids = broadcast.template.medias.all().values('file_id', 'file_type')
        buttons = list(broadcast.template.template_buttons.values('text', 'url').order_by('order'))
    else:
        content = broadcast.cleaned_content
        file_ids = broadcast.medias.all().values('file_id', 'file_type')
        buttons = list(broadcast.broadcast_buttons.values('text', 'url').order_by('order'))

    reply_markup = None
    if buttons:
        reply_markup = dict()
        reply_markup['inline_keyboard'] = []
        for button in buttons:
            reply_markup['inline_keyboard'].append(
                [{
                    'text': button['text'],
                    'url': button['url'],
                }]
            )

    for group in groups:
        if file_ids:
            file_type = file_ids[0]['file_type']
            if len(file_ids) > 1:
                response = methods.send_multi_file_by_file_id(
                    chat_id=group,
                    file_type=file_type,
                    file_ids=[file['file_id'] for file in file_ids],
                    caption=content
                )
            else:
                response = methods.send_file(
                    chat_id=group,
                    file_type=file_type,
                    file_id=file_ids[0]['file_id'],
                    caption=content,
                    reply_markup=reply_markup
                )
        else:
            response = methods.send_text(
                chat_id=group,
                text=content,
                reply_markup=reply_markup,
            )

        if response.status_code == 200:
            counter += 1

    broadcast.is_sent = True
    broadcast.percent = f"{round(counter / len(groups), 2) * 100} %"
    broadcast.save(update_fields=['is_sent', 'percent'])


@shared_task
def remove_files():
    medias = broadcast_models.Media.objects.filter(
        file_id__isnull=False
    )
    if not medias:
        return

    for media in medias:
        media.file.delete(save=False)
        media.file = None

    broadcast_models.Media.objects.bulk_update(medias, ['file'])

