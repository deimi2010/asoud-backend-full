from django.db.models import Q

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
