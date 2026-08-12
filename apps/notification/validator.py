async def validate_user(scope):
    """Consumers trust only the central ASGI authentication middleware."""
    scoped_user = scope.get('user')
    if scoped_user is not None and scoped_user.is_authenticated:
        return scoped_user if scoped_user.is_active else None
    return None
