from apps.base.models import models, BaseModel
from apps.users.models import User
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.fields import ArrayField
# Create your models here.

class Line(BaseModel):
    number = models.CharField(
        max_length=26,
        verbose_name=_('Number'),
        unique=True
    )

    estimated_cost = models.FloatField(
        verbose_name=_('EstimatedCost')
    )

    is_active = models.BooleanField(
        verbose_name=_('IsActive'),
        default=True
    )


class Template(BaseModel):
    template_id = models.IntegerField(
        verbose_name=_('TemplateID'),
        unique=True
    )

    content = models.TextField(
        verbose_name=_('Content')
    )

    variables = models.JSONField(
        verbose_name=_('Variables'),
        help_text=_("Please write in Json format")
    )

    estimated_cost = models.FloatField(
        verbose_name=_('EstimatedCost')
    )

    is_active = models.BooleanField(
        verbose_name=_('IsActive'),
        default=True
    )


class Contact(BaseModel):
    mobile_number = models.CharField(
        max_length=15,
        verbose_name=_('Mobile_number'),
        unique=True
    )

    name = models.CharField(
        max_length=64,
        verbose_name=_('Name'),
        null=True,
        blank=True
    )

    class Meta:
        db_table='Contact'
        verbose_name=_('Contact')
        verbose_name_plural=_('Contacts')

    def __str__(self):
        return self.mobile_number
    

class BaseSmsModel(BaseModel):
    user = models.ForeignKey(
        User,
        null=True,                      # for admin actions, null is allowed
        blank=True,
        on_delete=models.DO_NOTHING     # keep the info for later monetary calculations
    )
    
    to = ArrayField(
        models.CharField(
            max_length=16,
        ),
        verbose_name=_('SMSTo')
    )

    cost = models.FloatField(
        verbose_name=_('Cost')
    )

    actual_cost = models.FloatField(
        verbose_name=_('Actual_cost'),
        null=True,
        blank=True
    )

    def  __str__(self):
        return f'sms {str(self.id)[:4]}'
    
class BulkSms(BaseSmsModel):
    PENDING = 'pending'
    REJECTED = 'rejected'
    VERIFIED = 'verified'

    STATUS_CHOICES = [
        (PENDING, _('Pending')),
        (REJECTED, _('Rejected')),
        (VERIFIED, _('Verified'))
    ]

    content = models.TextField(
        verbose_name=_('Content'),
        null=True,
        blank=True,
    )

    line = models.ForeignKey(
        Line,
        on_delete=models.CASCADE,
        verbose_name=_('Number')
    )
    
    status = models.CharField(
        max_length=12,
        verbose_name=_('Status'),
        choices=STATUS_CHOICES,
        default=PENDING
    )

    message_ids = ArrayField(
        models.CharField(
            max_length=32
        ),
        verbose_name=_('Message_ids'),
        null=True,
        blank=True
    )

    packId = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        verbose_name=_('PackID')
    )
    
    class Meta:
        db_table = 'bulkSms'
        verbose_name = _('BulkSms')
        verbose_name_plural = _('BulkSms')

class PatternSms(BaseSmsModel):
    template = models.ForeignKey(
        Template,
        on_delete=models.DO_NOTHING
    )
    
    message_id = models.CharField(
        max_length=32,
        verbose_name=_('Message_ids'),
        null=True,
        blank=True
    )

    class Meta:
        db_table = "patternSms"
        verbose_name = _('PatternSms')
        verbose_name_plural = _('PatternSms')
