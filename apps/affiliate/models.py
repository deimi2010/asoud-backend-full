from apps.base.models import models, BaseModel
from django.utils.translation import gettext_lazy as _
from apps.market.models import Market
from apps.category.models import SubCategory
from apps.product.models import ProductKeyword, Product
from apps.users.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal

# Create your models here.

class AffiliateProductTheme(BaseModel):
    market = models.ForeignKey(
        Market,
        on_delete=models.CASCADE,
        verbose_name=_('Market'),
    )
    name = models.CharField(
        max_length=100,
        verbose_name=_('Name'),
    )
    order = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_('Order'),
    )

    class Meta:
        db_table = 'affiliate_product_theme'
        verbose_name = _('Affiliate Product theme')
        verbose_name_plural = _('Affiliate Product themes')

    def __str__(self):
        return self.name


class AffiliateProduct(BaseModel):
    MARKET = "market"
    CUSTOMER = "customer"
    FREE = "free"

    SHIP_COST_PAY_TYPE_CHOICES = (
        (MARKET, _("Market")),
        (CUSTOMER, _("Customer")),
        (FREE, _("Free")),
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

    ONLINE = "online"
    PERSON = "person"
    BOTH = "both"

    SELL_TYPE_CHOICES = (
        (ONLINE, _("Online")),
        (PERSON, _("Person")),
        (BOTH, _("Both")),
    )

    NEW = "new"
    SPECIAL_OFFER = "special_offer"
    COMING_SOON = "coming_soon"
    NONE = "none"

    TAG_CHOICES = (
        (NEW, _("New")),
        (SPECIAL_OFFER, _("Special Offer")),
        (COMING_SOON, _("Coming Soon")),
        (NONE, _("None")),
    )

    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"

    TAG_POSITION_CHOICES = (
        (TOP_LEFT, _("Top Left")),
        (TOP_RIGHT, _("Top Right")),
        (BOTTOM_LEFT, _("Bottom Left")),
        (BOTTOM_RIGHT, _("Bottom Right")),
    )

    market = models.ForeignKey(
        Market,
        on_delete=models.CASCADE,
        related_name='affiliate_products',
        verbose_name=_('Market'),
    )

    product = models.ForeignKey(
        Product,
        related_name="affiliates",
        on_delete=models.CASCADE,
        verbose_name=_('Product')
    )
    
    type = models.CharField(
        max_length=20,
        verbose_name=_('Type'),
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

    technical_detail = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Technical detail'),
    )

    sub_category = models.ForeignKey(
        SubCategory,
        on_delete=models.CASCADE,
        verbose_name=_('Category'),
    )

    keywords = models.ManyToManyField(
        ProductKeyword,
        related_name='affiliate_products',
        blank=True,
        verbose_name=_('Keywords'),
    )

    stock = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Stock'),
    )

    price = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        verbose_name=_('Main price'),
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=DRAFT,
        verbose_name=_('Status'),
    )

    required_product = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='dependent_affiliate_products',
        help_text="Another product that is required for this product.",
        verbose_name=_('Required product'),
    )

    gift_product = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='gift_affiliate_products',
        verbose_name=_('Gift product'),
    )

    is_requirement = models.BooleanField(
        default=False,
        verbose_name=_('Is requirement'),
    )

    tag = models.CharField(
        max_length=20,
        choices=TAG_CHOICES,
        default=NONE,
        verbose_name=_("Tag"),
    )

    tag_position = models.CharField(
        max_length=20,
        choices=TAG_POSITION_CHOICES,
        default=TOP_LEFT,
        verbose_name=_("Tag Position"),
    )

    sell_type = models.CharField(
        max_length=10,
        choices=SELL_TYPE_CHOICES,
        default=ONLINE,
        verbose_name=_('Sell type'),
    )

    ship_cost = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        blank=True,
        null=True,
        verbose_name=_('Ship cost'),
    )

    ship_cost_pay_type = models.CharField(
        max_length=10,
        choices=SHIP_COST_PAY_TYPE_CHOICES,
        verbose_name=_('Ship cost pay type')
    )

    theme = models.ForeignKey(
        AffiliateProductTheme,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='affiliate_products',
        verbose_name=_('Theme')
    )

    class Meta:
        db_table = 'affiliate_product'
        verbose_name = _('Affiliate Product')
        verbose_name_plural = _('Affiliate Products')
        constraints = [
            models.UniqueConstraint(
                fields=('market', 'product'),
                name='unique_affiliate_product_per_market',
            ),
        ]

    def __str__(self):
        return self.name


class AffiliateProductImage(BaseModel):
    product = models.ForeignKey(
        AffiliateProduct,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name=_('Affiliate Product')
    )

    image = models.ImageField(
        upload_to='product/affiliate/image/',
        verbose_name=_('Image'),
    )

    class Meta:
        db_table = 'affiliate_product_image'
        verbose_name = _('Affiliate Product image')
        verbose_name_plural = _('Affiliate Product images')

    def __str__(self):
        return self.product.name


class AffiliateCommission(BaseModel):
    HELD = 'held'
    AVAILABLE = 'available'
    PAID = 'paid'
    REVERSED = 'reversed'
    STATUS_CHOICES = (
        (HELD, _('Held')),
        (AVAILABLE, _('Available')),
        (PAID, _('Paid')),
        (REVERSED, _('Reversed')),
    )

    order = models.ForeignKey(
        'cart.Order', on_delete=models.PROTECT, related_name='affiliate_commissions',
    )
    order_item = models.OneToOneField(
        'cart.OrderItem', on_delete=models.PROTECT,
        related_name='affiliate_commission',
    )
    affiliate_product = models.ForeignKey(
        AffiliateProduct, on_delete=models.PROTECT, related_name='commissions',
    )
    seller = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='affiliate_sales',
    )
    marketer = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='affiliate_earnings',
    )
    quantity = models.PositiveIntegerField()
    customer_total = models.DecimalField(max_digits=14, decimal_places=3)
    seller_total = models.DecimalField(max_digits=14, decimal_places=3)
    gross_commission = models.DecimalField(max_digits=14, decimal_places=3)
    platform_fee = models.DecimalField(
        max_digits=14, decimal_places=3, default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))],
    )
    marketer_total = models.DecimalField(max_digits=14, decimal_places=3)
    status = models.CharField(
        max_length=12, choices=STATUS_CHOICES, default=HELD, db_index=True,
    )
    available_at = models.DateTimeField(blank=True, null=True, db_index=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    seller_status = models.CharField(
        max_length=12, choices=STATUS_CHOICES, default=HELD, db_index=True,
    )
    seller_available_at = models.DateTimeField(blank=True, null=True, db_index=True)
    seller_paid_at = models.DateTimeField(blank=True, null=True)
    reversal_reason = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ('-created_at',)
        indexes = [
            models.Index(fields=('marketer', 'status'), name='affiliate_earning_status_idx'),
            models.Index(fields=('seller', 'status'), name='affiliate_sale_status_idx'),
        ]


class AffiliatePayout(BaseModel):
    REQUESTED = 'requested'
    APPROVED = 'approved'
    PAID = 'paid'
    REJECTED = 'rejected'
    STATUS_CHOICES = (
        (REQUESTED, _('Requested')),
        (APPROVED, _('Approved')),
        (PAID, _('Paid')),
        (REJECTED, _('Rejected')),
    )
    MARKETER_ROLE = 'marketer'
    SELLER_ROLE = 'seller'
    ROLE_CHOICES = (
        (MARKETER_ROLE, _('Marketer')),
        (SELLER_ROLE, _('Seller')),
    )

    marketer = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='affiliate_payouts',
    )
    commissions = models.ManyToManyField(
        AffiliateCommission, related_name='payouts', blank=True,
    )
    amount = models.DecimalField(
        max_digits=14, decimal_places=3,
        validators=[MinValueValidator(Decimal('1'))],
    )
    status = models.CharField(
        max_length=12, choices=STATUS_CHOICES, default=REQUESTED, db_index=True,
    )
    role = models.CharField(
        max_length=10, choices=ROLE_CHOICES, default=MARKETER_ROLE,
    )
    tracking_code = models.CharField(max_length=100, blank=True, default='')
    admin_note = models.TextField(blank=True, default='')
    paid_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ('-created_at',)
