import asyncio

asyncio.set_event_loop(asyncio.new_event_loop())

from django.core.management.base import BaseCommand
from django.core.cache import cache

from responder.client import build_client
from responder.services import sync_group_users
from responder import models as r_models


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            asyncio.run(self.main())
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("User to‘xtatildi (Ctrl+C)"))

    async def main(self):
        client = build_client()
        await client.start()
        try:
            while True:
                # signal bormi?
                if cache.get("telegram_sync_required"):
                    cache.delete("telegram_sync_required")

                    groups = r_models.TelegramGroup.objects.filter(
                        is_active=True)

                    await sync_group_users(client, groups)

                    # # blacklist update
                    # r_models.Verification.objects.exclude(
                    #     chat_id__in=group_ids
                    # ).update(is_blacklisted=False)

                await asyncio.sleep(5)

        finally:
            await client.stop()
