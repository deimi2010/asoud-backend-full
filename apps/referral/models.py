from apps.base.models import models, BaseModel
from apps.users.models import User
from django.utils.translation import gettext_lazy as _
# Create your models here.

class Referral(BaseModel):
    referred_by = models.ForeignKey(
        User,
        related_name='referrals_made',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Referred By")
    )
    referred_user = models.OneToOneField(
        User,
        related_name='referral',
        on_delete=models.CASCADE,
        verbose_name=_("Referred User")
    )

    def __str__(self):
        return f"{self.referred_user} referred by {self.referred_by}"
