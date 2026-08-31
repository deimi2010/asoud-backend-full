import time

from django.core.management.base import BaseCommand

from apps.notification.services import NotificationQueueProcessor
from apps.reserve.lifecycle import process_appointment_reminders
from apps.reserve.services import expire_stale_holds


class Command(BaseCommand):
    help = 'Expire stale holds, send appointment reminders, and retry notifications.'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true')
        parser.add_argument('--interval', type=int, default=60)
        parser.add_argument('--batch-size', type=int, default=100)

    def handle(self, *args, **options):
        while True:
            expired = expire_stale_holds()
            reminders = process_appointment_reminders(batch_size=options['batch_size'])
            notifications = NotificationQueueProcessor().process_queue(options['batch_size'])
            self.stdout.write(
                f'expired={expired} reminders={reminders} notifications={notifications}'
            )
            if options['once']:
                return
            time.sleep(max(10, options['interval']))
