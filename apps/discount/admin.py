from django.contrib import admin
from apps.base.admin import BaseAdmin
from apps.discount.models import Discount
# Register your models here.

class DiscountAdmin(BaseAdmin):
    list_display = [
        'code',
        'limitation',
        'expiry',
        'is_valid'
    ]

    fields = (
        'code',
        'position',
        'percentage',
        'expiry',
        'users',
        'limitation',
        'consumed',
        'object_id'
    ) + BaseAdmin.fields

    readonly_fields = BaseAdmin.readonly_fields


admin.site.register(Discount, DiscountAdmin)

