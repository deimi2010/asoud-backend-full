import os
import uuid
from apps.base.models import models, BaseModel
from apps.users.models import User
from django.utils.translation import gettext_lazy as _
# Create your models here.

def upload_inquiry_image(instance, filename):
    _, extension = os.path.splitext(filename)
    extension = extension.lower()
    return f"img/inquiry/{uuid.uuid4()}{extension}"

def upload_inquiry_answer_image(instance, filename):
    _, extension = os.path.splitext(filename)
    extension = extension.lower()
    return f"img/inquiry_answer/{uuid.uuid4()}{extension}"

class Inquiry(BaseModel):
    GOOD = 'good'
    SERVICE = 'service'

    TYPE_CHOICES = [
        (GOOD, _('Good')),
        (SERVICE, _('Service')),
    ]

    SMS = 'sms'
    CHAT = 'chat'

    SEND_CHOICES = [
        (SMS, _('Sms')),
        (CHAT, _('Chat')),
    ]

    user = models.ForeignKey(
        User,
        related_name="inquiries",
        on_delete=models.CASCADE,
        verbose_name=_('User')
    )

    type = models.CharField(
        max_length=16,
        choices=TYPE_CHOICES,
        verbose_name=_('Type'),
    )

    name = models.CharField(
        max_length=50,
        verbose_name=_('Name')
    )

    technical_detail = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Technical Detail')
    )

    amount = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        verbose_name=_('Amount')
    )

    unit = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        verbose_name=_('Unit')
    )

    expiry = models.DateTimeField(
        verbose_name=_('Expiry')
    )

    send = models.CharField(
        max_length=5,
        choices=SEND_CHOICES,
        null=True,
        blank=True,
        default=None,
        verbose_name=_('Send')
    )

    class Meta:
        db_table = "inquiry"
        ordering = ['-created_at', 'expiry']
        verbose_name = _('Price Inquiry')
        verbose_name_plural = _('Price Inquiries')

    def __str__(self):
        return self.name

class InquiryImage(BaseModel):
    inquiry = models.ForeignKey(
        Inquiry,
        related_name="images",
        on_delete=models.CASCADE
    )

    image = models.ImageField(
        upload_to=upload_inquiry_image
    )

    class Meta:
        db_table = "inquiry_image"
        verbose_name = _('Inquiry Image')
        verbose_name_plural = _('Inquiry Images')

    def __str__(self):
        return str(self.id)[:4]

class InquiryAnswer(BaseModel):
    inquiry = models.ForeignKey(
        Inquiry,
        related_name="answers",
        on_delete=models.CASCADE,
        verbose_name=_('Inquiry')
    )

    user = models.ForeignKey(
        User,
        related_name='inquiry_answers',
        on_delete=models.CASCADE,
        verbose_name=_('User')
    )
    
    detail = models.TextField(
        verbose_name=_('Detail')
    )

    total = models.CharField(
        max_length=15,
        verbose_name=_('Total Price')
    )

    fee = models.CharField(
        max_length=15,
        null=True,
        blank=True,
        verbose_name=_('Fee')
    )

    class Meta:
        db_table = "inquiry_answer"
        ordering = ['-created_at']
        verbose_name = _('Inquiry Answer')
        verbose_name_plural = _('Inquiry Answers')

    def __str__(self):
        return str(self.id)[:4]
    
class InquiryAnswerImage(BaseModel):
    answer = models.ForeignKey(
        InquiryAnswer,
        related_name="images",
        on_delete=models.CASCADE
    )

    image = models.ImageField(
        upload_to=upload_inquiry_answer_image
    )

    class Meta:
        db_table = "inquiry_answer_image"
        verbose_name = _('Inquiry Answer Image')
        verbose_name_plural = _('Inquiry Answer Images')

    def __str__(self):
        return str(self.id)[:4]
