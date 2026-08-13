from rest_framework import permissions


class IsPlatformAdmin(permissions.BasePermission):
    """Access allowed only to staff/admin users."""

    message = "Only platform administrators may access this endpoint."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "is_active", False)
            and getattr(request.user, "is_staff", False)
        )


class IsAuthenticatedUser(permissions.BasePermission):
    """Access allowed to any authenticated user."""

    message = "Authentication is required."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "is_active", True)
        )


class IsStoreOwner(permissions.BasePermission):
    """Access allowed only to users who own at least one store."""

    message = "Only store owners may access this endpoint."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if not getattr(request.user, "is_active", True):
            return False

        if getattr(request.user, "is_staff", False):
            return True

        return request.user.markets.exists()

    def has_object_permission(self, request, view, obj):
        if not self.has_permission(request, view):
            return False
        if getattr(request.user, "is_staff", False):
            return True

        market = getattr(obj, "market", obj)
        owner_id = getattr(market, "user_id", None)
        return owner_id == request.user.id
