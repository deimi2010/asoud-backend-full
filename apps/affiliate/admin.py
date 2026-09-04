from apps.base.admin import admin, BaseAdmin, BaseTabularInline
from apps.affiliate.models import (
    AffiliateProduct,
    AffiliateProductImage,
    AffiliateProductTheme
    , AffiliateCommission, AffiliatePayout
)
from django.utils import timezone
# Register your models here.


class AffiliateProductImageTabularInline(BaseTabularInline):
    model = AffiliateProductImage

    fields = (
        'image',
    ) + BaseTabularInline.fields

    readonly_fields = BaseTabularInline.readonly_fields

class AffiliateProductAdmin(BaseAdmin):
    inlines = [
        AffiliateProductImageTabularInline,
    ]

    list_display = [
        'name',
        'product',
        'market'
    ]

    fields = (
        'market',
        'product',
        'type',
        'name',
        'description',
        'technical_detail',
        'sub_category',
        'keywords',
        'stock',
        'price',
        'status',
        'required_product',
        'gift_product',
        'tag',
        'tag_position',
        'sell_type',
        'ship_cost',
        'ship_cost_pay_type'
    ) + BaseAdmin.fields

    readonly_fields = BaseAdmin.readonly_fields

admin.site.register(AffiliateProduct, AffiliateProductAdmin)


class AffiliateProductThemeAdmin(BaseAdmin):
    list_display = [
        'market',
    ]

    fields = (
        'market',
        'name',
        'order',
    ) + BaseAdmin.fields

    readonly_fields = BaseAdmin.readonly_fields

admin.site.register(AffiliateProductTheme, AffiliateProductThemeAdmin)


@admin.register(AffiliateCommission)
class AffiliateCommissionAdmin(BaseAdmin):
    list_display = ('order', 'marketer', 'seller', 'marketer_total', 'status', 'available_at')
    list_filter = ('status',)
    readonly_fields = (
        'order', 'order_item', 'affiliate_product', 'seller', 'marketer',
        'quantity', 'customer_total', 'seller_total', 'gross_commission',
        'platform_fee', 'marketer_total',
    ) + BaseAdmin.readonly_fields


@admin.register(AffiliatePayout)
class AffiliatePayoutAdmin(BaseAdmin):
    list_display = ('marketer', 'role', 'amount', 'status', 'tracking_code', 'created_at')
    list_filter = ('role', 'status')
    filter_horizontal = ('commissions',)

    def save_model(self, request, obj, form, change):
        previous = AffiliatePayout.objects.filter(pk=obj.pk).values_list(
            'status', flat=True,
        ).first()
        if obj.status == AffiliatePayout.PAID and previous != AffiliatePayout.PAID:
            obj.paid_at = timezone.now()
        super().save_model(request, obj, form, change)
        if obj.status == AffiliatePayout.PAID:
            if obj.role == AffiliatePayout.MARKETER_ROLE:
                obj.commissions.filter(
                    status=AffiliateCommission.AVAILABLE,
                ).update(
                    status=AffiliateCommission.PAID,
                    paid_at=obj.paid_at,
                    updated_at=timezone.now(),
                )
            else:
                obj.commissions.filter(
                    seller_status=AffiliateCommission.AVAILABLE,
                ).update(
                    seller_status=AffiliateCommission.PAID,
                    seller_paid_at=obj.paid_at,
                    updated_at=timezone.now(),
                )


