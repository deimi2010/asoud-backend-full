from django.core.management.base import BaseCommand, CommandError

from apps.payment.core import reconcile_stale_payment_sessions


class Command(BaseCommand):
    help = 'Reconcile stale gateway sessions; release only definitive failures.'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=100)

    def handle(self, *args, **options):
        limit = options['limit']
        if limit < 1:
            raise CommandError('--limit must be positive')
        result = reconcile_stale_payment_sessions(limit=limit)
        self.stdout.write(
            self.style.SUCCESS(
                'Checked {checked}; completed {completed}; released {released}; '
                'ambiguous {ambiguous}.'.format(**result)
            )
        )
