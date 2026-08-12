"""
Management command to process notification queue
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.notification.services import NotificationQueueProcessor
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process queued notifications'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of notifications to process in one batch'
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Clean up old notifications after processing'
        )
        parser.add_argument(
            '--cleanup-days',
            type=int,
            default=30,
            help='Number of days to keep notifications (for cleanup)'
        )
    
    def handle(self, *args, **options):
        batch_size = options['batch_size']
        cleanup = options['cleanup']
        cleanup_days = options['cleanup_days']
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting notification processing with batch size {batch_size}')
        )
        
        try:
            # Process notifications
            processor = NotificationQueueProcessor()
            results = processor.process_queue(batch_size)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Processed {results["processed"]} notifications, '
                    f'{results["failed"]} failed'
                )
            )
            
            # Cleanup if requested
            if cleanup:
                self.stdout.write('Cleaning up old notifications...')
                deleted_count = processor.cleanup_old_notifications(cleanup_days)
                self.stdout.write(
                    self.style.SUCCESS(f'Cleaned up {deleted_count} old notifications')
                )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error processing notifications: {e}')
            )
            logger.error(f"Error in process_notifications command: {e}")
            raise

