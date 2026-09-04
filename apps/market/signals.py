from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.market.models import BusinessCardProfile, Market


@receiver(post_save, sender=Market)
def ensure_business_card_profile(sender, instance, created, **kwargs):
    if created:
        BusinessCardProfile.objects.get_or_create(market=instance)
