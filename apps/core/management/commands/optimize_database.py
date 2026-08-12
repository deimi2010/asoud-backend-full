"""
Management command for database optimization
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from apps.core.database_optimization import DatabaseOptimizer, DatabaseMaintenance
from apps.core.caching import CacheWarming
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Optimize database performance'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--create-indexes',
            action='store_true',
            help='Create optimized indexes',
        )
        parser.add_argument(
            '--analyze-performance',
            action='store_true',
            help='Analyze query performance',
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Clean up old data',
        )
        parser.add_argument(
            '--vacuum',
            action='store_true',
            help='Run VACUUM and ANALYZE',
        )
        parser.add_argument(
            '--health-check',
            action='store_true',
            help='Check database health',
        )
        parser.add_argument(
            '--warm-cache',
            action='store_true',
            help='Warm up cache',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Run all optimization tasks',
        )
    
    def handle(self, *args, **options):
        optimizer = DatabaseOptimizer()
        
        if options['all'] or options['create_indexes']:
            self.stdout.write('Creating optimized indexes...')
            optimizer.create_optimized_indexes()
            self.stdout.write(self.style.SUCCESS('Indexes created successfully'))
        
        if options['all'] or options['analyze_performance']:
            self.stdout.write('Analyzing query performance...')
            optimizer.analyze_query_performance()
            self.stdout.write(self.style.SUCCESS('Performance analysis completed'))
        
        if options['all'] or options['cleanup']:
            self.stdout.write('Cleaning up old data...')
            DatabaseMaintenance.cleanup_old_data()
            self.stdout.write(self.style.SUCCESS('Data cleanup completed'))
        
        if options['all'] or options['vacuum']:
            self.stdout.write('Running VACUUM and ANALYZE...')
            optimizer.vacuum_and_analyze()
            self.stdout.write(self.style.SUCCESS('VACUUM and ANALYZE completed'))
        
        if options['all'] or options['health_check']:
            self.stdout.write('Checking database health...')
            DatabaseMaintenance.check_database_health()
            self.stdout.write(self.style.SUCCESS('Health check completed'))
        
        if options['all'] or options['warm_cache']:
            self.stdout.write('Warming up cache...')
            cache_warmer = CacheWarming()
            cache_warmer.warm_popular_products()
            cache_warmer.warm_verified_markets()
            cache_warmer.warm_analytics_data()
            self.stdout.write(self.style.SUCCESS('Cache warming completed'))
        
        if not any(options.values()):
            self.stdout.write(self.style.WARNING('No optimization tasks specified. Use --help for options.'))


