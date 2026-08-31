from apps.base.models import models, BaseModel
from apps.users.models import User
from django.utils.translation import gettext_lazy as _
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
        unique=True,
        null=True,
        blank=True,
    )

    content = models.TextField(
        verbose_name=_('Content')
    )

    variables = models.JSONField(
        verbose_name=_('Variables'),
        help_text=_("Please write in Json format"),
        default=list,
        blank=True,
    )

    estimated_cost = models.FloatField(
        verbose_name=_('EstimatedCost')
    )

    is_active = models.BooleanField(
        verbose_name=_('IsActive'),
        default=True
    )
    owner = models.ForeignKey(
        User,
        related_name='sms_templates',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=100, blank=True, default='')
    category = models.CharField(max_length=32, blank=True, default='general')
    approval_status = models.CharField(
        max_length=16,
        choices=(
            ('pending', _('Pending')),
            ('approved', _('Approved')),
            ('rejected', _('Rejected')),
            ('needs_editing', _('Needs editing')),
        ),
        default='approved',
        db_index=True,
    )
    is_public = models.BooleanField(default=True)
    review_note = models.TextField(blank=True, default='')
    reviewed_by = models.ForeignKey(
        User,
        related_name='reviewed_sms_templates',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)


class Contact(BaseModel):
    mobile_number = models.CharField(
        max_length=15,
        verbose_name=_('Mobile_number'),
    )

    name = models.CharField(
        max_length=64,
        verbose_name=_('Name'),
        null=True,
        blank=True
    )
    user = models.ForeignKey(
        User,
        related_name='sms_contacts',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    source = models.CharField(
        max_length=16,
        choices=(('phone', _('Phone')), ('excel', _('Excel')), ('manual', _('Manual'))),
        default='manual',
    )
    has_consent = models.BooleanField(default=False)

    class Meta:
        db_table='Contact'
        verbose_name=_('Contact')
        verbose_name_plural=_('Contacts')
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'mobile_number'),
                name='unique_sms_contact_per_user',
            ),
        ]

    def __str__(self):
        return self.mobile_number
    

class BaseSmsModel(BaseModel):
    user = models.ForeignKey(
        User,
        null=True,                      # for admin actions, null is allowed
        blank=True,
        on_delete=models.DO_NOTHING     # keep the info for later monetary calculations
    )
    
    to = models.JSONField(
        default=list,
        verbose_name=_('SMSTo'),
        help_text=_('List of destination mobile numbers'),
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

    message_ids = models.JSONField(
        verbose_name=_('Message_ids'),
        null=True,
        blank=True,
        help_text=_('List of provider message identifiers'),
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


class SmsTariff(BaseModel):
    title = models.CharField(max_length=100)
    persian_first_segment_chars = models.PositiveSmallIntegerField(default=70)
    persian_next_segment_chars = models.PositiveSmallIntegerField(default=67)
    latin_first_segment_chars = models.PositiveSmallIntegerField(default=160)
    latin_next_segment_chars = models.PositiveSmallIntegerField(default=153)
    price_per_segment = models.DecimalField(max_digits=14, decimal_places=3)
    effective_from = models.DateTimeField()
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = 'sms_tariff'
        ordering = ('-effective_from',)

    def __str__(self):
        return self.title


class SmsCampaign(BaseModel):
    DRAFT = 'draft'
    WAITING_APPROVAL = 'waiting_approval'
    READY_FOR_PAYMENT = 'ready_for_payment'
    QUEUED = 'queued'
    SENDING = 'sending'
    SENT = 'sent'
    PARTIALLY_SENT = 'partially_sent'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    STATUS_CHOICES = (
        (DRAFT, _('Draft')),
        (WAITING_APPROVAL, _('Waiting approval')),
        (READY_FOR_PAYMENT, _('Ready for payment')),
        (QUEUED, _('Queued')),
        (SENDING, _('Sending')),
        (SENT, _('Sent')),
        (PARTIALLY_SENT, _('Partially sent')),
        (FAILED, _('Failed')),
        (CANCELLED, _('Cancelled')),
    )

    user = models.ForeignKey(User, related_name='sms_campaigns', on_delete=models.PROTECT)
    market = models.ForeignKey(
        'market.Market',
        related_name='sms_campaigns',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    template = models.ForeignKey(
        Template,
        related_name='campaigns',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    tariff = models.ForeignKey(SmsTariff, on_delete=models.PROTECT)
    line = models.ForeignKey(Line, on_delete=models.PROTECT)
    title = models.CharField(max_length=100)
    message = models.TextField()
    link = models.URLField(max_length=500, blank=True, default='')
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default=DRAFT, db_index=True)
    recipient_count = models.PositiveIntegerField(default=0)
    segment_count = models.PositiveIntegerField(default=0)
    estimated_cost = models.DecimalField(max_digits=18, decimal_places=3, default=0)
    reserved_cost = models.DecimalField(max_digits=18, decimal_places=3, default=0)
    actual_cost = models.DecimalField(max_digits=18, decimal_places=3, default=0)
    provider_pack_id = models.CharField(max_length=64, blank=True, default='')
    idempotency_key = models.CharField(max_length=64, unique=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'sms_campaign'
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=('user', 'status'), name='sms_campaign_user_status_idx'),
            models.Index(fields=('status', 'scheduled_at'), name='sms_campaign_queue_idx'),
        ]

    def __str__(self):
        return self.title


class SmsRecipient(BaseModel):
    PENDING = 'pending'
    SENT = 'sent'
    DELIVERED = 'delivered'
    UNDELIVERED = 'undelivered'
    FAILED = 'failed'
    STATUS_CHOICES = (
        (PENDING, _('Pending')),
        (SENT, _('Sent')),
        (DELIVERED, _('Delivered')),
        (UNDELIVERED, _('Undelivered')),
        (FAILED, _('Failed')),
    )

    campaign = models.ForeignKey(SmsCampaign, related_name='recipients', on_delete=models.CASCADE)
    name = models.CharField(max_length=64, blank=True, default='')
    mobile_number = models.CharField(max_length=15)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=PENDING, db_index=True)
    provider_message_id = models.CharField(max_length=64, blank=True, default='')
    actual_cost = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    error_message = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'sms_recipient'
        constraints = [
            models.UniqueConstraint(
                fields=('campaign', 'mobile_number'),
                name='unique_sms_campaign_recipient',
            ),
        ]
