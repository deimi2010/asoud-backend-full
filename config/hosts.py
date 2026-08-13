from django_hosts import patterns, host

host_patterns = patterns(
    '',
    #host(r'', 'config.urls', name='main'),
    host(r'app', 'config.app_urls', name='app'),
    host(r'api', 'config.urls', name='api'),  # API subdomain should use main URLs
    host(r'(?P<market_id>[a-zA-Z0-9-]{4,})', 'config.market_urls', name='market'),
    host(r'.*', 'config.urls', name='main'),
)
