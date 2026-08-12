from apps.base.admin import admin, BaseAdmin
from apps.wallet.models import Wallet, Transaction

# Register your models here.

class WalletAdmin(BaseAdmin):
    list_display = ['user', 'balance']
    fields = (
        'user',
        'balance'
    ) + BaseAdmin.fields

admin.site.register(Wallet, WalletAdmin)


class TransactionAdmin(BaseAdmin):
    list_display = ['user', 'action', 'amount']
    fields = (
        'user',
        'from_wallet',
        'to_wallet',
        'action',
        'amount',
    ) + BaseAdmin.fields
admin.site.register(Transaction, TransactionAdmin)