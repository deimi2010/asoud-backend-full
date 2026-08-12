from django.utils.translation import gettext_lazy as _
from decimal import Decimal

from apps.base.models import models, BaseModel
from apps.users.models import User
from apps.product.models import Product
from apps.affiliate.models import AffiliateProduct

# Create your models here.

class Cart(BaseModel):
    """Cart model for managing user shopping cart"""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='cart',
        verbose_name=_('User')
    )

    class Meta:
        db_table = 'cart'
        verbose_name = _('Cart')
        verbose_name_plural = _('Carts')

    def __str__(self):
        return f"Cart for {self.user.username}"

    def total_price(self):
        """Calculate total price of items in cart"""
        return sum(item.total_price() for item in self.items.all())

    def total_items(self):
        """Calculate total number of items in cart"""
        return sum(item.quantity for item in self.items.all())

    def clear(self):
        """Clear all items from cart"""
        self.items.all().delete()


class CartItem(BaseModel):
    """Cart item model"""
    cart = models.ForeignKey(
        'Cart',
        related_name='items',
        on_delete=models.CASCADE,
        verbose_name=_('Cart')
    )
    product = models.ForeignKey(
        Product,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name=_('Product'),
    )
    affiliate = models.ForeignKey(
        AffiliateProduct,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        verbose_name=_('Affiliate Product')
    )
    quantity = models.PositiveSmallIntegerField(
        default=1,
        verbose_name=_('Quantity'),
    )

    class Meta:
        db_table = 'cart_item'
        verbose_name = _('Cart Item')
        verbose_name_plural = _('Cart Items')
        unique_together = ['cart', 'product', 'affiliate']

    def __str__(self):
        if self.product:
            name = self.product.name
        elif self.affiliate:
            name = self.affiliate.name
        else:
            name = "unknown"
        return f"{self.quantity} x {name}"

    def total_price(self):
        """Calculate total price for this cart item"""
        if self.product:
            price = self.product.main_price
        elif self.affiliate:
            price = self.affiliate.price
        else: 
            price = 0
        return price * self.quantity


class Order(BaseModel):
    CASH = "cash"
    ONLINE = "online"

    TYPE_CHOICES = (
        (CASH, _("Cash")),
        (ONLINE, _("Online")),
    )

    DRAFT = "draft"
    PENDING = "pending"
    PROCESSING = "processing"
    VERIFIED = "verified"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"

    STATUS_CHOICES = (
        (DRAFT, _("Draft")),
        (PENDING, _("Pending")),
        (PROCESSING, _("Processing")),
        (VERIFIED, _("Verified")),
        (REJECTED, _("Rejected")),
        (COMPLETED, _("Completed")),
        (FAILED, _("Failed")),
    )

    INVENTORY_NONE = "none"
    INVENTORY_RESERVED = "reserved"
    INVENTORY_CONFIRMED = "confirmed"
    INVENTORY_RELEASED = "released"
    INVENTORY_STATUS_CHOICES = (
        (INVENTORY_NONE, _("Not reserved")),
        (INVENTORY_RESERVED, _("Reserved")),
        (INVENTORY_CONFIRMED, _("Confirmed")),
        (INVENTORY_RELEASED, _("Released")),
    )

    user = models.ForeignKey(
        User,
        related_name="orders",
        on_delete=models.CASCADE,
        verbose_name=_('User')
    )
    description = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Description')
    )
    type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        verbose_name=_('Type'),
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=PENDING,
        verbose_name=_('Status'),
    )
    owner_description = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Owner Descriptions')
    )
    is_paid = models.BooleanField(
        default=False,
        verbose_name=_('Is Paid')
    )
    discount = models.ForeignKey(
        'discount.Discount',
        related_name='orders',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    discount_code_snapshot = models.CharField(max_length=16, blank=True, default='')
    discount_percentage_snapshot = models.PositiveSmallIntegerField(default=0)
    subtotal_amount = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=14, decimal_places=3, default=Decimal('0'))
    payable_amount = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    inventory_status = models.CharField(
        max_length=10,
        choices=INVENTORY_STATUS_CHOICES,
        default=INVENTORY_NONE,
    )
    
    class Meta:
        ordering = ['-created_at']
        db_table = 'order'
        verbose_name = _('Order')
        verbose_name_plural = _('Orders')
        indexes = [
            # Performance optimization indexes
            models.Index(fields=['user', 'status'], name='idx_order_user_status'),
            models.Index(fields=['user', 'created_at'], name='idx_order_user_created'),
            models.Index(fields=['status', 'is_paid'], name='idx_order_status_paid'),
            models.Index(fields=['is_paid', 'created_at'], name='idx_order_paid_created'),
            models.Index(fields=['type', 'status'], name='idx_order_type_status'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                condition=models.Q(status='draft'),
                name='uniq_draft_order_user',
            ),
        ]

    def __str__(self):
        return f"Order {str(self.id)[:6]}"

    def total_price(self):
        """Return the immutable placed-order total or the live draft total."""
        if self.payable_amount is not None:
            return self.payable_amount
        return sum((item.total_price() for item in self.items.all()), Decimal('0'))
    
    def total_items(self):
        return sum(item.quantity for item in self.items.all())
    
    @classmethod
    def get_or_create_order(cls, user):
        """Get or create a order (pending order) for the user"""
        order, created = cls.objects.get_or_create(
            user=user,
            status=cls.DRAFT,
            defaults={
                'type': cls.ONLINE,  # default to online, can be changed at checkout
                'description': 'Shopping order'
            }
        )
        return order

class OrderItem(BaseModel):
    order = models.ForeignKey(
        Order,
        related_name="items",
        on_delete=models.CASCADE,
        verbose_name=_('Order'),
    )
    product = models.ForeignKey(
        Product,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=_('Product'),
    )
    affiliate = models.ForeignKey(
        AffiliateProduct,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=_('Affiliate Product')
    )
    quantity = models.PositiveSmallIntegerField(
        default=1,
        verbose_name=_('Quantity'),
    )
    unit_price = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(product__isnull=False, affiliate__isnull=True)
                    | models.Q(product__isnull=True, affiliate__isnull=False)
                ),
                name='order_item_exactly_one_target',
            ),
        ]
        db_table = 'order_item'
        verbose_name = _('Order item')
        verbose_name_plural = _('Order items')

    def __str__(self):
        if self.product:
            name = self.product.name
        elif self.affiliate:
            name = self.affiliate.name
        else:
            name = "unknown"
        return f"{self.quantity} x {name}"

    def total_price(self):
        if self.unit_price is not None:
            price = self.unit_price
        elif self.product:
            price = self.product.main_price
        elif self.affiliate:
            price = self.affiliate.price
        else: 
            price = 0
        return price * self.quantity


