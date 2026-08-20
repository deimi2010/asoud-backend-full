from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.fields import GenericRelation

from apps.base.models import models, BaseModel

from apps.users.models import User
from apps.category.models import SubCategory
from apps.region.models import City
from apps.comment.models import Comment
from apps.market.upload import (
    upload_market_logo,
    upload_market_background,
    upload_market_userOnly,
    upload_market_slider
)
# Create your models here.


# old images are not removed, fix it later
class Market(BaseModel):
    COMPANY = "company"
    SHOP = "shop"

    TYPE_CHOICES = (
        (COMPANY, _("Company")),
        (SHOP, _("Shop")),
    )

    DRAFT = "draft"
    QUEUE = "queue"
    NOT_PUBLISHED = "not_published"
    PUBLISHED = "published"
    NEEDS_EDITING = "needs_editing"
    INACTIVE = "inactive"

    STATUS_CHOICES = (
        (DRAFT, _("Draft")),
        (QUEUE, _("In Queue for Publication")),
        (NOT_PUBLISHED, _("Not Published")),
        (PUBLISHED, _("Published")),
        (NEEDS_EDITING, _("Needs Editing")),
        (INACTIVE, _("Inactive")),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="markets",
        verbose_name=_('User'),
    )

    type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        verbose_name=_('Type'),
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=DRAFT,
        verbose_name=_('Status'),
    )

    status_reason = models.TextField(
        blank=True,
        default='',
        verbose_name=_('Status reason'),
    )

    is_paid = models.BooleanField(
        default=False,
        verbose_name=_('Is paid'),
    )

    subscription_start_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_('Subscription start date'),
    )

    subscription_end_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_('Subscription end date'),
    )

    business_id = models.CharField(
        max_length=63,
        unique=True,
        verbose_name=_('Business id'),
    )

    name = models.CharField(
        max_length=100,
        verbose_name=_('Name'),
    )

    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Description'),
    )

    national_code = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        verbose_name=_('National code'),
    )

    sub_category = models.ForeignKey(
        SubCategory,
        on_delete=models.CASCADE,
        verbose_name=_('Sub Category'),
    )

    slogan = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name=_('Slogan'),
    )

    logo_img = models.ImageField(
        upload_to=upload_market_logo,
        blank=True,
        null=True,
        verbose_name=_('Logo image'),
    )

    background_img = models.ImageField(
        upload_to=upload_market_background,
        blank=True,
        null=True,
        verbose_name=_('Background image'),
    )

    view_count = models.PositiveBigIntegerField(
        default=0,
        verbose_name=_('View count'),
    )

    comments = GenericRelation(
        Comment,
        related_query_name='market_comments',
    )

    user_only_img = models.ImageField(
        upload_to=upload_market_userOnly,
        blank=True,
        null=True,
        verbose_name=_('Image'),
        help_text=_('The image is not visible to the market owner.')
    )

    class Meta:
        db_table = 'market'
        verbose_name = _('Market')
        verbose_name_plural = _('Markets')
        indexes = [
            # Performance optimization indexes
            models.Index(fields=['user', 'status'], name='idx_market_user_status'),
            models.Index(fields=['status', 'created_at'], name='idx_market_status_created'),
            models.Index(fields=['sub_category', 'status'], name='idx_market_category_status'),
            models.Index(fields=['business_id'], name='idx_market_business_id'),
            models.Index(fields=['is_paid', 'status'], name='idx_market_paid_status'),
        ]

    def __str__(self):
        return self.name


class MarketRevision(BaseModel):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    STATUS_CHOICES = (
        (PENDING, _('Pending')),
        (APPROVED, _('Approved')),
        (REJECTED, _('Rejected')),
    )

    market = models.ForeignKey(
        Market,
        related_name='revisions',
        on_delete=models.CASCADE,
    )
    created_by = models.ForeignKey(
        User,
        related_name='market_revisions',
        on_delete=models.CASCADE,
    )
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=PENDING)
    reviewed_by = models.ForeignKey(
        User,
        related_name='reviewed_market_revisions',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default='')

    class Meta:
        indexes = [
            models.Index(fields=('market', 'status'), name='market_revision_status_idx'),
        ]


class MarketLocation(BaseModel):
    market = models.OneToOneField(
        Market,
        on_delete=models.CASCADE,
        related_name='location',
        verbose_name=_('Market'),
    )

    city = models.ForeignKey(
        City,
        on_delete=models.CASCADE,
        verbose_name=_('City'),
    )

    address = models.TextField(
        verbose_name=_('Address'),
    )

    zip_code = models.CharField(
        max_length=15,
        verbose_name=_('Zip code'),
    )

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
    )

    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
    )

    class Meta:
        db_table = 'market_location'
        verbose_name = _('Market location')
        verbose_name_plural = _('Market locations')

    def __str__(self):
        return self.market.name


class MarketContact(BaseModel):
    market = models.OneToOneField(
        Market,
        on_delete=models.CASCADE,
        related_name='contact',
        verbose_name=_('Market'),
    )

    first_mobile_number = models.CharField(
        max_length=15,
        verbose_name=_('First mobile number'),
    )

    second_mobile_number = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        verbose_name=_('Second mobile number'),
    )

    telephone = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        verbose_name=_('Telephone'),
    )

    fax = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        verbose_name=_('Fax'),
    )

    email = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        verbose_name=_('Email'),
    )

    website_url = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        verbose_name=_('Website url'),
    )

    messenger_ids = models.JSONField(
        blank=True,
        null=True,
        verbose_name=_('Messenger IDs'),
    )

    class Meta:
        db_table = 'market_contact'
        verbose_name = _('Market contact')
        verbose_name_plural = _('Market contacts')

    def __str__(self):
        return self.market.name


class MarketSlider(BaseModel):
    market = models.ForeignKey(
        Market,
        on_delete=models.CASCADE,
        related_name='slider',
        verbose_name=_('Market')
    )

    image = models.ImageField(
        upload_to=upload_market_slider,
        verbose_name=_('Image'),
    )

    url = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name=_('Url'),
    )

    class Meta:
        db_table = 'market_slider'
        verbose_name = _('Market slider')
        verbose_name_plural = _('Market sliders')

    def __str__(self):
        return self.market.name


class MarketTheme(BaseModel):
    market = models.OneToOneField(
        Market,
        related_name='theme',
        on_delete=models.CASCADE,
        verbose_name=_('Market'),
    )
    color = models.CharField(
        max_length=7,
        verbose_name=_('Color'),
        blank=True,
        null=True,
    )
    secondary_color = models.CharField(
        max_length=7,
        verbose_name=_('Color'),
        blank=True,
        null=True,
    )
    background_color = models.CharField(
        max_length=7,
        verbose_name=_('Color'),
        blank=True,
        null=True,
    )
    font = models.CharField(
        max_length=100,
        verbose_name=_('Font'),
        blank=True,
        null=True,
    )
    font_color = models.CharField(
        max_length=7,
        verbose_name=_('Font color'),
        blank=True,
        null=True,
    )
    secondary_font_color = models.CharField(
        max_length=7,
        verbose_name=_('Font color'),
        blank=True,
        null=True,
    )

    class Meta:
        db_table = 'market_theme'
        verbose_name = _('Market theme')
        verbose_name_plural = _('Market themes')

    def __str__(self):
        return f"{self.market}-{self.font}"


class MarketGatewayConnection(BaseModel):
    ASOUD = 'asoud'
    PERSONAL = 'personal'
    GATEWAY_TYPE_CHOICES = (
        (ASOUD, _('Asoud gateway')),
        (PERSONAL, _('Personal gateway')),
    )

    PENDING = 'pending'
    ACTIVE = 'active'
    REJECTED = 'rejected'
    STATUS_CHOICES = (
        (PENDING, _('Pending review')),
        (ACTIVE, _('Active')),
        (REJECTED, _('Rejected')),
    )

    market = models.OneToOneField(
        Market,
        related_name='gateway_connection',
        on_delete=models.CASCADE,
        verbose_name=_('Market'),
    )
    gateway_type = models.CharField(
        max_length=20,
        choices=GATEWAY_TYPE_CHOICES,
        verbose_name=_('Gateway type'),
    )
    user_code = models.CharField(
        max_length=255,
        blank=True,
        default='',
        verbose_name=_('Personal gateway user code'),
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING,
        verbose_name=_('Connection status'),
    )

    class Meta:
        db_table = 'market_gateway_connection'
        verbose_name = _('Market gateway connection')
        verbose_name_plural = _('Market gateway connections')

    def __str__(self):
        return f'{self.market}-{self.gateway_type}-{self.status}'


class MarketReport(BaseModel):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ARCHIVED = "archived"

    STATUS_CHOICES = [
        (DRAFT, _("Draft")),
        (IN_PROGRESS, _("In Progress")),
        (COMPLETED, _("Completed")),
        (ARCHIVED, _("Archived")),
    ]

    market = models.ForeignKey(
        Market,
        on_delete=models.CASCADE,
        verbose_name=_('Market'),
    )
    creator = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        verbose_name=_('Creator'),
        null=True,
    )
    description = models.TextField(
        verbose_name=_('Description'),
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=DRAFT,
        verbose_name=_('Status'),
    )

    class Meta:
        db_table = 'market_report'
        verbose_name = _('Market report')
        verbose_name_plural = _('Market reports')

    def __str__(self):
        return self.market.name


class MarketBookmark(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='bookmarks',
        verbose_name=_('User'),
    )
    market = models.ForeignKey(
        Market,
        on_delete=models.CASCADE,
        related_name='bookmarked_by',
        verbose_name=_('Market'),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Is active'),
    )

    class Meta:
        db_table = 'market_bookmark'
        unique_together = ('user', 'market')
        verbose_name = _('Market bookmark')
        verbose_name_plural = _('Market bookmarks')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} bookmarked {self.market}"


class MarketLike(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='likes',
        verbose_name=_('User'),
    )
    market = models.ForeignKey(
        Market,
        on_delete=models.CASCADE,
        related_name='liked_by',
        verbose_name=_('Market'),
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Is active'),
    )

    class Meta:
        db_table = 'market_like'
        unique_together = ('user', 'market')
        verbose_name = _('Market like')
        verbose_name_plural = _('Market likes')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} liked {self.market}"


class MarketView(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='viewed_markets',
        verbose_name=_('User'),
    )
    market = models.ForeignKey(
        Market,
        on_delete=models.CASCADE,
        related_name='viewed_by',
        verbose_name=_('Market'),
    )

    class Meta:
        db_table = 'market_view'
        unique_together = ('user', 'market')
        verbose_name = _('Market view')
        verbose_name_plural = _('Market views')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} bookmarked {self.market}"


class MarketDiscount(BaseModel):
    market = models.ForeignKey(
        Market,
        on_delete=models.CASCADE,
        verbose_name=_('Market'),
    )
    code = models.CharField(
        max_length=10,
        verbose_name=_('Code'),
    )
    title = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name=_('Title'),
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Description'),
    )
    percentage = models.PositiveSmallIntegerField(
        verbose_name=_('Percentage'),
    )
    usage_count = models.PositiveBigIntegerField(
        default=0,
        verbose_name=_('View count'),
    )

    class Meta:
        db_table = 'market_discount'
        verbose_name = _('Market discount')
        verbose_name_plural = _('Market discounts')

    def __str__(self):
        return self.code


class MarketSchedule(BaseModel):
    DAYS_OF_WEEK = [
        (0, _('Saturday')),
        (1, _('Sunday')),
        (2, _('Monday')),
        (3, _('Tuesday')),
        (4, _('Wednesday')),
        (5, _('Thursday')),
        (6, _('Friday')),
    ]

    market = models.ForeignKey(
        Market,
        related_name='schedules',
        on_delete=models.CASCADE,
        verbose_name=_('Market'),
    )
    day_of_week = models.PositiveSmallIntegerField(
        choices=DAYS_OF_WEEK,
        verbose_name=_('Day of week'),
    )
    start_time = models.TimeField(
        verbose_name=_('Start time'),
    )
    end_time = models.TimeField(
        verbose_name=_('End time'),
    )

    class Meta:
        db_table = 'market_schedule'
        unique_together = ('market', 'day_of_week', 'start_time', 'end_time')
        ordering = ['day_of_week', 'start_time']

    def __str__(self):
        day_name = dict(self.DAYS_OF_WEEK).get(self.day_of_week, "Unknown")
        return f"{self.market.name}: {day_name} {self.start_time} - {self.end_time}"


class MarketMembership(BaseModel):
    MANAGER = 'manager'
    EDITOR = 'editor'
    VIEWER = 'viewer'
    ROLE_CHOICES = (
        (MANAGER, _('Manager')),
        (EDITOR, _('Editor')),
        (VIEWER, _('Viewer')),
    )

    market = models.ForeignKey(
        Market,
        related_name='memberships',
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        User,
        related_name='market_memberships',
        on_delete=models.CASCADE,
    )
    role = models.CharField(max_length=16, choices=ROLE_CHOICES, default=EDITOR)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'market_membership'
        constraints = [
            models.UniqueConstraint(
                fields=('market', 'user'),
                name='unique_market_member',
            ),
        ]
        indexes = [
            models.Index(fields=('user', 'is_active'), name='market_member_active_idx'),
        ]
