from django_hosts.middleware import HostsBaseMiddleware
from django.urls import NoReverseMatch, set_urlconf, get_urlconf
from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from django_hosts.resolvers import (
    get_host_patterns,
    get_host
)
import re

class HostsRequestMiddleware(HostsBaseMiddleware):
    def process_request(self, request):
        # Extract the host from the request
        request_host = request.get_host().split(':')[0]  # Remove port if present
        # Find the best match for the host
        host, kwargs = self.get_best_match(request_host)

        # Set the URLconf and host on the request
        request.urlconf = host.urlconf
        request.host = host

        # Temporarily override the URLconf to allow reversing host URLs
        current_urlconf = get_urlconf()
        try:
            set_urlconf(host.urlconf)
            return host.callback(request, **kwargs)
        finally:
            # Reset URLconf for this thread
            set_urlconf(current_urlconf)

    def get_best_match(self, request_host):
        """
        Find the best matching host pattern for the given request host.
        Prioritizes the empty subdomain pattern if no subdomain is present.
        """
        host_patterns = get_host_patterns()

        subdomain = request_host.split('.')[0]
        domains = settings.ALLOWED_HOSTS
        # Check if subdomain matches any domain pattern
        
        # Check if the request host matches any subdomain pattern
        for host in host_patterns:
            
            compiled_regex = re.compile(host.regex)
            if request_host != 'asoud.ir' and compiled_regex.match(request_host):  # Use the compiled regex to match
                return host, compiled_regex.match(request_host).groupdict()
            
        if any([subdomain in domain for domain in domains]):
            return [host for host in host_patterns if host.regex==''][0], {}    # main
        # Fall back to the default host
        try:
            return get_host(settings.DEFAULT_HOST), {}
        except AttributeError:
            raise ImproperlyConfigured("Missing DEFAULT_HOST setting")
