from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

from apps.base.models import models, BaseModel
from apps.users.models import User

# Create your models here.


class Comment(BaseModel):
    # Generic relation fields
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
    )

    object_id = models.UUIDField()

    content_object = GenericForeignKey(
        'content_type',
        'object_id',
    )

    # Comment-specific fields
    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name=_('Creator'),
    )

    content = models.TextField(
        verbose_name=_('Content'),
    )

    parent_comment = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        related_name='replies',
        null=True,
        blank=True,
        verbose_name=_('Parent comment'),
    )

    class Meta:
        db_table = 'comment'
        verbose_name = _('Comment')
        verbose_name_plural = _('Comments')

    def __str__(self):
        return self.content
