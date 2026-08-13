from django.db.models import Q
from django.shortcuts import get_object_or_404

from apps.market.models import Market, MarketMembership


WRITE_ROLES = (MarketMembership.MANAGER, MarketMembership.EDITOR)
READ_ROLES = (*WRITE_ROLES, MarketMembership.VIEWER)


def accessible_markets(user, *, write=False):
    """Markets visible to an owner, active colleague, or platform admin."""
    markets = Market.objects.all()
    if user.is_staff:
        return markets
    roles = WRITE_ROLES if write else READ_ROLES
    return markets.filter(
        Q(user=user)
        | Q(
            memberships__user=user,
            memberships__is_active=True,
            memberships__role__in=roles,
        )
    ).distinct()


def market_access_filter(prefix, user, *, write=False):
    """Build a Q filter for models related to Market through ``prefix``."""
    if user.is_staff:
        return Q()
    roles = WRITE_ROLES if write else READ_ROLES
    return Q(**{f'{prefix}user': user}) | Q(
        **{
            f'{prefix}memberships__user': user,
            f'{prefix}memberships__is_active': True,
            f'{prefix}memberships__role__in': roles,
        }
    )


def lock_accessible_market(*, market_id, user, write=False):
    """Authorize through membership joins, then lock only the market table.

    PostgreSQL rejects ``FOR UPDATE`` on the DISTINCT/outer-join query required
    for membership access. Keeping authorization and the row lock as separate
    queries avoids locking nullable joined rows while preserving tenant scope.
    Callers must already be inside ``transaction.atomic``.
    """
    authorized_id = get_object_or_404(
        accessible_markets(user, write=write).values('id'),
        id=market_id,
    )['id']
    return get_object_or_404(
        Market.objects.select_for_update(),
        id=authorized_id,
    )
