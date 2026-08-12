from apps.base.admin import admin, BaseAdmin, BaseTabularInline

from apps.cart.models import (
    Order,
    OrderItem
)

# Register your models here.


class OrderItemTabularInlune(BaseTabularInline):
    model = OrderItem
    extra = 0

    fields = (
        'product',
        'affiliate',
        'quantity',
        'total_price',
    ) + BaseTabularInline.fields

    readonly_fields = (
        'total_price',
    ) + BaseTabularInline.readonly_fields

    def total_price(self, obj):
        return obj.total_price()
    total_price.short_description = 'Total price'


class OrderAdmin(BaseAdmin):
    inlines = [
        OrderItemTabularInlune,
    ]

    list_display = [
        'user',
        'total_price',
        'total_items',
        'type',
        'status',
    ]

    fields = (
        'user',
        'total_price',
        'total_items',
        'description',
        'type',
        'status'
    ) + BaseAdmin.fields

    readonly_fields = (
        'total_price',
        'total_items',
    ) + BaseAdmin.readonly_fields

    def total_price(self, obj):
        return obj.total_price()
    total_price.short_description = 'Total price'

    def total_items(self, obj):
        return obj.total_items()
    total_items.short_description = 'Total items'


admin.site.register(Order, OrderAdmin)

class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'product', 'affiliate', 'quantity', 'total_price')

admin.site.register(OrderItem, OrderItemAdmin)