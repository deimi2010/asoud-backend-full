"""Migration validation settings for a fresh, disposable development database.

Production must not use this module. Its complete baseline exists only because
the historical repository has no reconciled production migration graph.
"""

from .local import *  # noqa: F401,F403


DEV_MIGRATED_APPS = [
    'advertise', 'affiliate', 'analytics', 'base', 'cart', 'category', 'chat',
    'comment', 'core', 'discount', 'flutter', 'gateway', 'information',
    'market', 'market_subdomain', 'notification', 'payment', 'price_inquiry',
    'product', 'referral', 'region', 'reserve', 'sms', 'users', 'wallet',
]

MIGRATION_MODULES = {
    app_label: f'dev_migrations.{app_label}'
    for app_label in DEV_MIGRATED_APPS
}
