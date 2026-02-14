from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message
from responder.models import TelegramUser


class SaveMessageMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
            event: Message,
            data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message):
            user_tg = event.from_user

            TelegramUser.objects.get_or_create(
                telegram_id=user_tg.id,
                defaults={
                    'username': user_tg.username,
                    'first_name': user_tg.first_name,
                    'last_name': user_tg.last_name
                }
            )

        return await handler(event, data)
