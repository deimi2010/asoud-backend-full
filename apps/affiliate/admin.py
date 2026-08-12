from apps.base.admin import admin, BaseAdmin, BaseTabularInline
from apps.affiliate.models import (
    AffiliateProduct,
    AffiliateProductImage,
    AffiliateProductTheme
)
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




