from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid
# Create your models here.


class BaseModel(models.Model):
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        blank=True,
        null=True,
        verbose_name=_('Created at'),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        blank=True,
        null=True,
        verbose_name=_('Updated at'),
    )

    class Meta:
        abstract = True
