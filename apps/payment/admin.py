from apps.base.admin import admin, BaseAdmin
from apps.payment.models import Payment, Zarinpal
# Register your models here.

class PaymentAdmin(BaseAdmin):
    list_display = [
        'id',
        'amount',
        'target',
        'status',
        'created_at'
    ]
    list_filter = [
        'status',
    ]
    fields = (
        'user',
        'amount',
        'target_content_type',
        'target_id',
        'gateway_content_type',
        'gateway_id',
        'status',
    ) + BaseAdmin.fields

admin.site.register(Payment, PaymentAdmin)


class ZarinpalAdmin(BaseAdmin):
    list_display = [
        'id',
        'payment',
        'authority',
        'transaction_id',
    ]
    search_fields = [
        'transaction_id'
    ]

    fields = (
        'payment',
        'authority',
        'transaction_id',
        'verification_data',
    ) + BaseAdmin.fields

admin.site.register(Zarinpal, ZarinpalAdmin)