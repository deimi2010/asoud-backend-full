from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from apps.base.models import models, BaseModel

# Create your models here.


class Term(BaseModel):
    title = models.CharField(
        max_length=200,
        default="Terms and Conditions",
        verbose_name=_("Title"),
    )

    content = models.TextField(
        help_text=_("The full text of the terms and conditions."),
        verbose_name=_("Content"),
    )

    class Meta:
        db_table = 'term'
        verbose_name = _('Terms and conditions')
        verbose_name_plural = _('Terms and conditions')

    def save(self, *args, **kwargs):
        # Enforce singleton behavior
        if Term.objects.exists() and not self.pk:
            raise ValidationError(
                _("Only one instance of Term is allowed."),
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    @classmethod
    def get_solo(cls):
        # Retrieve the first singleton instance
        instance = cls.objects.first()
        if instance is None:
            raise cls.DoesNotExist("No Term instance exists.")
        return instance


class VoiceGuide(BaseModel):
    market_file = models.FileField(
        upload_to='guide/',
        blank=True,
        null=True,
        verbose_name=_('Market file'),
    )
    product_file = models.FileField(
        upload_to='product/',
        blank=True,
        null=True,
        verbose_name=_('Product file'),
    )

    class Meta:
        db_table = 'voice_guide'
        verbose_name = _('Voice guide')
        verbose_name_plural = _('Voice guide')

    def save(self, *args, **kwargs):
        # Enforce singleton behavior
        if VoiceGuide.objects.exists() and not self.pk:
            raise ValidationError(
                _("Only one instance of VoiceGuide is allowed."),
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return 'Voice guide'

    @classmethod
    def get_solo(cls):
        # Retrieve the first singleton instance
        instance = cls.objects.first()
        if instance is None:
            raise cls.DoesNotExist("No VoiceGuide instance exists.")
        return instance
