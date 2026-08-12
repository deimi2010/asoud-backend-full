from django_hosts import patterns, host
from django.conf import settings

host_patterns = patterns(
    '',
    #host(r'', 'config.urls', name='main'),
    host(r'app', 'config.app_urls', name='app'),
    host(r'api', 'config.urls', name='api'),  # API subdomain should use main URLs
    host(r'(?P<market_id>[a-zA-Z0-9-]{4,})\.asoud\.ir', 'config.market_urls', name='market'),  # Dynamic pattern for subdomains
    host(r'', 'config.urls', name='main'),
)
