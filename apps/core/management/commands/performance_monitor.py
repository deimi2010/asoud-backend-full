"""
Performance Monitoring Command for ASOUD Platform
"""

import time
import psutil
import requests
import json
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.utils import timezone
from apps.core.database_optimization import DatabaseOptimizer
from apps.core.caching import cache_manager
from apps.core.performance import QueryProfiler
import logging

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """Performance monitoring utilities"""
    
    def __init__(self):
        self.start_time = time.time()
        self.metrics = {}
    
    def collect_system_metrics(self):
        """Collect system performance metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used = memory.used / (1024**3)  # GB
            memory_total = memory.total / (1024**3)  # GB
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_used = disk.used / (1024**3)  # GB
            disk_total = disk.total / (1024**3)  # GB
            
            # Network I/O
            network = psutil.net_io_counters()
            network_bytes_sent = network.bytes_sent / (1024**2)  # MB
            network_bytes_recv = network.bytes_recv / (1024**2)  # MB
            
            self.metrics['system'] = {
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'memory_used_gb': round(memory_used, 2),
                'memory_total_gb': round(memory_total, 2),
                'disk_percent': disk_percent,
                'disk_used_gb': round(disk_used, 2),
                'disk_total_gb': round(disk_total, 2),
                'network_sent_mb': round(network_bytes_sent, 2),
                'network_recv_mb': round(network_bytes_recv, 2),
                'timestamp': timezone.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    def collect_database_metrics(self):
        """Collect database performance metrics"""
        try:
            with connection.cursor() as cursor:
                # Get database size
                cursor.execute("SELECT pg_database_size(current_database());")
                db_size_bytes = cursor.fetchone()[0]
                db_size_gb = db_size_bytes / (1024**3)
                
                # Get connection count
                cursor.execute("SELECT count(*) FROM pg_stat_activity;")
                connection_count = cursor.fetchone()[0]
                
                # Get slow queries
                cursor.execute("""
                    SELECT query, mean_time, calls, total_time
                    FROM pg_stat_statements
                    WHERE mean_time > 100
                    ORDER BY mean_time DESC
                    LIMIT 10;
                """)
                slow_queries = cursor.fetchall()
                
                # Get table sizes
                cursor.execute("""
                    SELECT 
                        tablename,
                        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
                    FROM pg_tables
                    WHERE schemaname = 'public'
                    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                    LIMIT 10;
                """)
                table_sizes = cursor.fetchall()
                
                self.metrics['database'] = {
                    'size_gb': round(db_size_gb, 2),
                    'connection_count': connection_count,
                    'slow_queries': [
                        {
                            'query': query[:100] + '...' if len(query) > 100 else query,
                            'mean_time_ms': round(mean_time, 2),
                            'calls': calls,
                            'total_time_ms': round(total_time, 2)
                        }
                        for query, mean_time, calls, total_time in slow_queries
                    ],
                    'largest_tables': [
                        {'table': table, 'size': size}
                        for table, size in table_sizes
                    ],
                    'timestamp': timezone.now().isoformat(),
                }
                
        except Exception as e:
            logger.error(f"Error collecting database metrics: {e}")
    
    def collect_cache_metrics(self):
        """Collect cache performance metrics"""
        try:
            # Redis cache stats
            if hasattr(cache_manager, 'redis_available') and cache_manager.redis_available:
                cache_stats = cache_manager.get_stats()
            else:
                cache_stats = {'error': 'Redis not available'}
            
            # Django cache stats
            cache_info = cache._cache.get_client().info()
            
            self.metrics['cache'] = {
                'redis_stats': cache_stats,
                'django_cache_info': {
                    'used_memory': cache_info.get('used_memory_human'),
                    'connected_clients': cache_info.get('connected_clients'),
                    'total_commands_processed': cache_info.get('total_commands_processed'),
                    'keyspace_hits': cache_info.get('keyspace_hits'),
                    'keyspace_misses': cache_info.get('keyspace_misses'),
                },
                'timestamp': timezone.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Error collecting cache metrics: {e}")
    
    def collect_application_metrics(self):
        """Collect application performance metrics"""
        try:
            # Get Django settings
            debug_mode = settings.DEBUG
            secret_key_set = bool(settings.SECRET_KEY)
            
            # Security check
            if debug_mode:
                logger.warning("DEBUG mode is enabled in production!")
            if not secret_key_set:
                logger.error("SECRET_KEY is not set!")
            
            # Get installed apps count
            installed_apps_count = len(settings.INSTALLED_APPS)
            
            # Get middleware count
            middleware_count = len(settings.MIDDLEWARE)
            
            # Get database settings
            database_engine = settings.DATABASES['default']['ENGINE']
            database_name = settings.DATABASES['default']['NAME']
            
            self.metrics['application'] = {
                'debug_mode': debug_mode,
                'secret_key_set': secret_key_set,
                'installed_apps_count': installed_apps_count,
                'middleware_count': middleware_count,
                'database_engine': database_engine,
                'database_name': database_name,
                'timestamp': timezone.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Error collecting application metrics: {e}")
    
    def test_api_endpoints(self, base_url='http://localhost:8000'):
        """Test API endpoints performance"""
        try:
            endpoints = [
                '/api/v1/user/products/',
                '/api/v1/user/markets/',
                '/api/v1/user/order/',
                '/health/',
            ]
            
            api_metrics = {}
            
            for endpoint in endpoints:
                try:
                    start_time = time.time()
                    response = requests.get(f"{base_url}{endpoint}", timeout=10)
                    end_time = time.time()
                    
                    response_time = (end_time - start_time) * 1000  # Convert to milliseconds
                    
                    api_metrics[endpoint] = {
                        'status_code': response.status_code,
                        'response_time_ms': round(response_time, 2),
                        'success': response.status_code < 400,
                        'content_length': len(response.content),
                    }
                    
                except Exception as e:
                    api_metrics[endpoint] = {
                        'status_code': 0,
                        'response_time_ms': 0,
                        'success': False,
                        'error': str(e),
                    }
            
            self.metrics['api'] = {
                'endpoints': api_metrics,
                'timestamp': timezone.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Error testing API endpoints: {e}")
    
    def generate_report(self):
        """Generate performance report"""
        report = {
            'monitoring_session': {
                'start_time': timezone.now().isoformat(),
                'duration_seconds': round(time.time() - self.start_time, 2),
            },
            'metrics': self.metrics,
            'recommendations': self._generate_recommendations(),
        }
        
        return report
    
    def _generate_recommendations(self):
        """Generate performance recommendations"""
        recommendations = []
        
        # System recommendations
        if 'system' in self.metrics:
            system = self.metrics['system']
            
            if system['cpu_percent'] > 80:
                recommendations.append("High CPU usage detected - consider optimizing queries or scaling")
            
            if system['memory_percent'] > 80:
                recommendations.append("High memory usage detected - consider increasing memory or optimizing caching")
            
            if system['disk_percent'] > 90:
                recommendations.append("High disk usage detected - consider cleaning up old files or increasing storage")
        
        # Database recommendations
        if 'database' in self.metrics:
            db = self.metrics['database']
            
            if db['connection_count'] > 50:
                recommendations.append("High database connection count - consider connection pooling")
            
            if len(db['slow_queries']) > 0:
                recommendations.append("Slow queries detected - consider optimizing database queries")
            
            if db['size_gb'] > 10:
                recommendations.append("Large database size - consider archiving old data")
        
        # Cache recommendations
        if 'cache' in self.metrics:
            cache_metrics = self.metrics['cache']
            
            if 'redis_stats' in cache_metrics:
                redis_stats = cache_metrics['redis_stats']
                
                if redis_stats.get('hit_rate', 0) < 80:
                    recommendations.append("Low cache hit rate - consider optimizing cache strategy")
        
        # API recommendations
        if 'api' in self.metrics:
            api_metrics = self.metrics['api']
            
            for endpoint, metrics in api_metrics.get('endpoints', {}).items():
                if metrics.get('response_time_ms', 0) > 1000:
                    recommendations.append(f"Slow API endpoint: {endpoint} - consider optimization")
        
        return recommendations

class Command(BaseCommand):
    help = 'Monitor system performance and generate report'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--output-file',
            type=str,
            help='Output file for performance report',
        )
        parser.add_argument(
            '--test-api',
            action='store_true',
            help='Test API endpoints performance',
        )
        parser.add_argument(
            '--api-url',
            type=str,
            default='http://localhost:8000',
            help='API base URL for testing',
        )
        parser.add_argument(
            '--monitor-duration',
            type=int,
            default=60,
            help='Monitoring duration in seconds',
        )
    
    def handle(self, *args, **options):
        self.stdout.write('🔍 Starting Performance Monitoring...')
        
        monitor = PerformanceMonitor()
        
        # Collect metrics
        self.stdout.write('📊 Collecting system metrics...')
        monitor.collect_system_metrics()
        
        self.stdout.write('🗄️ Collecting database metrics...')
        monitor.collect_database_metrics()
        
        self.stdout.write('💾 Collecting cache metrics...')
        monitor.collect_cache_metrics()
        
        self.stdout.write('⚙️ Collecting application metrics...')
        monitor.collect_application_metrics()
        
        if options['test_api']:
            self.stdout.write('🌐 Testing API endpoints...')
            monitor.test_api_endpoints(options['api_url'])
        
        # Generate report
        self.stdout.write('📋 Generating performance report...')
        report = monitor.generate_report()
        
        # Output report
        if options['output_file']:
            with open(options['output_file'], 'w') as f:
                json.dump(report, f, indent=2)
            self.stdout.write(f'✅ Report saved to {options["output_file"]}')
        else:
            self.stdout.write('📊 Performance Report:')
            self.stdout.write(json.dumps(report, indent=2))
        
        # Display recommendations
        recommendations = report.get('recommendations', [])
        if recommendations:
            self.stdout.write('\n💡 Recommendations:')
            for i, rec in enumerate(recommendations, 1):
                self.stdout.write(f'{i}. {rec}')
        
        self.stdout.write('\n✅ Performance monitoring completed!')
