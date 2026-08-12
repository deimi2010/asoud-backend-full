from django.core.management.base import BaseCommand, CommandError

from apps.analytics.models import MLModelArtifact
from apps.analytics.services import (
    ModelTrainer,
    acquire_training_lock,
    release_training_lock,
)


class Command(BaseCommand):
    help = 'Train versioned Analytics/ML artifacts without exposing a training API.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--models',
            nargs='+',
            choices=[MLModelArtifact.RECOMMENDER, MLModelArtifact.DEMAND, MLModelArtifact.RFM],
            default=[MLModelArtifact.RECOMMENDER, MLModelArtifact.DEMAND, MLModelArtifact.RFM],
        )
        parser.add_argument('--activate-if-better', action='store_true')

    def handle(self, *args, **options):
        token = acquire_training_lock()
        if token is None:
            raise CommandError('Another analytics model training run is active.')
        try:
            artifacts = ModelTrainer().train(
                options['models'],
                activate_if_better=options['activate_if_better'],
            )
        finally:
            release_training_lock(token)
        for artifact in artifacts:
            self.stdout.write(self.style.SUCCESS(
                f'{artifact.model_type} version={artifact.version} '
                f'samples={artifact.sample_count} active={artifact.is_active}'
            ))
