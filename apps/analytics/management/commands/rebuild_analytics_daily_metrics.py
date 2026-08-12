from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.analytics.services import DailyMetricBuilder


class Command(BaseCommand):
    help = 'Rebuild authoritative daily metrics for a rolling date window.'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=7)

    def handle(self, *args, **options):
        days = max(1, min(options['days'], 366))
        end = timezone.localdate()
        start = end - timedelta(days=days - 1)
        rebuilt = DailyMetricBuilder().rebuild(start, end)
        self.stdout.write(self.style.SUCCESS(
            f'Rebuilt {rebuilt} day(s), {start.isoformat()} through {end.isoformat()}.'
        ))
