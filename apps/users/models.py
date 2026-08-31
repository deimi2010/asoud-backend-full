from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractUser
from pathlib import Path
from uuid import uuid4

from .managers import CustomUserManager
from apps.base.models import BaseModel

# Create your models here.


class User(AbstractUser):
    """A platform identity, not an exclusive business role.

    ``type`` is retained for backwards compatibility with existing clients and
    data. Authorization must be derived from staff flags and resource
    relationships (markets, affiliate records, etc.), never from this field.
    """
    USER = "user"
    OWNER = "owner"
    MARKETER = "marketer"

    TYPE_CHOICES = (
        (USER, _("User")),
        (OWNER, _("Owner")),
        (MARKETER, _("Marketer")),
    )

    # Authentication
    username = None
    mobile_number = models.CharField(
        unique=True,
        max_length=15,
        verbose_name=_('Mobile number'),
    )
    pin = models.CharField(
        max_length=5,
        null=True,
        blank=True,
        verbose_name=_('Pin'),
    )
    pin_expiry = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Pin expiry'),
        db_index=True,  # Index for cleanup of expired PINs
    )
    last_activity = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Last activity'),
        db_index=True,  # Index for activity tracking
    )
    type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        default=USER,
        verbose_name=_('Type'),
        db_index=True,  # Index for filtering by user type
    )

    USERNAME_FIELD = "mobile_number"
    REQUIRED_FIELDS = []
    objects = CustomUserManager()

    class Meta:
        db_table = 'user'
        verbose_name = _('User')
        verbose_name_plural = _('Users')

    def __str__(self):
        return self.mobile_number

    def is_owner(self):
        return self.markets.exists()

    @property
    def can_manage_platform(self):
        return self.is_staff and self.is_active

    @property
    def can_create_market(self):
        return self.is_authenticated and self.is_active

class UserProfile(BaseModel):
    PENDING = 'pending'
    NEEDS_EDITING = 'needs_editing'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    INACTIVE = 'inactive'
    STATUS_CHOICES = (
        (PENDING, _('Pending review')),
        (NEEDS_EDITING, _('Needs editing')),
        (APPROVED, _('Approved')),
        (REJECTED, _('Rejected')),
        (INACTIVE, _('Inactive')),
    )

    PHONE_UNCHECKED = 'unchecked'
    PHONE_POSSESSION_VERIFIED = 'possession_verified'
    PHONE_OWNER_MATCHED = 'owner_matched'
    PHONE_OWNER_MISMATCHED = 'owner_mismatched'
    PHONE_MANUAL_REVIEW = 'manual_review'
    PHONE_STATUS_CHOICES = (
        (PHONE_UNCHECKED, _('Unchecked')),
        (PHONE_POSSESSION_VERIFIED, _('Possession verified by OTP')),
        (PHONE_OWNER_MATCHED, _('Legal owner matched')),
        (PHONE_OWNER_MISMATCHED, _('Legal owner mismatched')),
        (PHONE_MANUAL_REVIEW, _('Manual review required')),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        verbose_name=_('User'),
    )
    address = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Address'),
    )
    national_code = models.CharField(
        max_length=10,
        verbose_name=_('National code'),
    )
    birth_date = models.DateField(
        blank=True,
        null=True,
        verbose_name=_('Birth date'),
    )
    iban_number = models.CharField(
        max_length=26,
        blank=True,
        null=True,
        verbose_name=_('Iban number'),
    )
    picture = models.ImageField(
        upload_to='user/picture/',
        blank=True,
        null=True,
        verbose_name=_('Image'),
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING,
        db_index=True,
    )
    phone_ownership_status = models.CharField(
        max_length=24,
        choices=PHONE_STATUS_CHOICES,
        default=PHONE_UNCHECKED,
    )
    review_note = models.TextField(blank=True, default='')
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User,
        related_name='reviewed_user_profiles',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = 'user_profile'
        verbose_name = _('User profile')
        verbose_name_plural = _('User profiles')

    def __str__(self):
        return self.user.mobile_number


def upload_identity_document(instance, filename):
    extension = Path(filename).suffix.lower()[:10]
    return f'private/user/{instance.user_id}/{instance.document_type}/{uuid4().hex}{extension}'


class UserDocument(BaseModel):
    NATIONAL_CARD_FRONT = 'national_card_front'
    NATIONAL_CARD_BACK = 'national_card_back'
    BIRTH_CERTIFICATE = 'birth_certificate'
    SELFIE_WITH_ID = 'selfie_with_id'
    BANK_OWNERSHIP = 'bank_ownership'
    ACTIVITY_LICENSE = 'activity_license'
    DOCUMENT_TYPE_CHOICES = (
        (NATIONAL_CARD_FRONT, _('National card front')),
        (NATIONAL_CARD_BACK, _('National card back')),
        (BIRTH_CERTIFICATE, _('Birth certificate')),
        (SELFIE_WITH_ID, _('Selfie with identity document')),
        (BANK_OWNERSHIP, _('Bank account ownership evidence')),
        (ACTIVITY_LICENSE, _('Activity license or supporting document')),
    )

    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    STATUS_CHOICES = (
        (PENDING, _('Pending review')),
        (APPROVED, _('Approved')),
        (REJECTED, _('Rejected')),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_('User document'),
    )
    file = models.FileField(
        upload_to=upload_identity_document,
        blank=True,
        null=True,
        verbose_name=_('Market file'),
    )
    document_type = models.CharField(
        max_length=32,
        choices=DOCUMENT_TYPE_CHOICES,
        default=ACTIVITY_LICENSE,
    )
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=PENDING)
    review_note = models.TextField(blank=True, default='')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        User,
        related_name='reviewed_user_documents',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = 'user_document'
        verbose_name = _('User document')
        verbose_name_plural = _('User documents')
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'document_type'),
                name='unique_user_identity_document_type',
            ),
        ]

    def __str__(self):
        return self.user.mobile_number


class UserColleague(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_('User'),
    )
    mobile_number = models.CharField(
        unique=True,
        max_length=15,
        verbose_name=_('Mobile number'),
    )

    class Meta:
        db_table = 'user_colleague'
        verbose_name = _('User colleague')
        verbose_name_plural = _('User colleagues')

    def __str__(self):
        return self.user.mobile_number


class BankInfo(BaseModel):
    name = models.CharField(max_length=16, unique=True)
    logo = models.ImageField(
        upload_to='bank/logo/',
        blank=True,
        null=True,
        verbose_name=_('logo'),
    )
    def __str__(self):
        return self.name
    

class UserBankInfo(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='banks',
        verbose_name=_('User'),
    )
    bank_info = models.ForeignKey(
        BankInfo,
        on_delete=models.CASCADE,
        related_name='bankinfoes',
        verbose_name=_('Bank info'),
    )
    card_number = models.CharField(
        unique=True,
        max_length=19,
        verbose_name=_('Card number'),
    )
    account_number = models.CharField(
        unique=True,
        max_length=32,
        verbose_name=_('Account number'),
    )
    iban = models.CharField(
        max_length=32,
        blank=True,
        null=True,
        verbose_name=_('Iban number'),
    )
    full_name = models.CharField(
        max_length=128,
        verbose_name=_('Full name'),
    )
    branch_id = models.PositiveSmallIntegerField(
        verbose_name=_('Branch id'),
    )
    branch_name = models.CharField(
        max_length=20,
        verbose_name=_('Branch name'),
    )
    description = models.TextField(null=True, blank=True)
    def __str__(self):
        return self.card_number


class LoginAttempt(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='login_attempts',
        verbose_name=_('User'),
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_('IP address'),
    )
    user_agent = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('User agent'),
    )
    success = models.BooleanField(default=False)

    class Meta:
        db_table = 'login_attempt'
        verbose_name = _('Login attempt')
        verbose_name_plural = _('Login attempts')

    def __str__(self):
        return f"{self.user.mobile_number} - {'success' if self.success else 'failed'}"
