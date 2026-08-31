import time

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.sms.models import SmsCampaign
from apps.sms.services import send_campaign


class Command(BaseCommand):
    help = 'Process paid commercial SMS campaigns from the durable database queue.'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true')
        parser.add_argument('--interval', type=int, default=5)

    def handle(self, *args, **options):
        while True:
            campaign = SmsCampaign.objects.filter(
                status=SmsCampaign.QUEUED,
            ).filter(
                scheduled_at__isnull=True,
            ).order_by('created_at').first()
            if campaign is None:
                campaign = SmsCampaign.objects.filter(
                    status=SmsCampaign.QUEUED,
                    scheduled_at__lte=timezone.now(),
                ).order_by('scheduled_at').first()
            if campaign:
                send_campaign(campaign)
            if options['once']:
                return
            time.sleep(max(1, options['interval']))
