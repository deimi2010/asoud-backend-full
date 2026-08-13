from django.db.models import Q

from apps.market.models import Market


def viewable_markets(user):
    if not user or not user.is_authenticated or not user.is_active:
        return Market.objects.none()
    query = Market.objects.all()
    if user.is_staff or user.is_superuser:
        return query
    return query.filter(
        Q(user=user)
        | Q(memberships__user=user, memberships__is_active=True)
        | Q(
            customer_accesses__user=user,
            customer_accesses__is_active=True,
            status=Market.PUBLISHED,
        )
    ).distinct()
