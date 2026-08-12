"""Trusted request identity helpers used by security controls."""

from __future__ import annotations

from ipaddress import ip_address, ip_network

from django.conf import settings


def _valid_ip(value):
    if not value:
        return None
    try:
        return str(ip_address(value.strip()))
    except ValueError:
        return None


def _is_trusted_proxy(remote_address):
    remote = _valid_ip(remote_address)
    if remote is None:
        return False
    configured = getattr(settings, "ASOUD_TRUSTED_PROXY_CIDRS", ())
    for value in configured:
        try:
            if ip_address(remote) in ip_network(value, strict=False):
                return True
        except ValueError:
            continue
    return False


def get_client_ip(request):
    """Return a validated IP without trusting client-supplied forwarding headers."""

    remote = _valid_ip(request.META.get("REMOTE_ADDR"))
    if remote is None:
        return "unknown"

    if not _is_trusted_proxy(remote):
        return remote

    # The edge proxy must overwrite, rather than append, this header. XFF is
    # deliberately ignored because an unsanitised chain is attacker-controlled.
    forwarded = _valid_ip(request.META.get("HTTP_X_REAL_IP"))
    return forwarded or remote
