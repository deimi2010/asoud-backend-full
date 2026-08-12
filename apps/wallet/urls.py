from django.urls import path
from apps.wallet.views import (
    WalletBalanceView,
    WalletCheckView,
    TransactionListView,
    WalletPayView
)

app_name = "wallet"


urlpatterns = [
    path(
        'balance/', 
        WalletBalanceView.as_view(), 
        name="balance"
    ),
    path(
        'balance/check/', 
        WalletCheckView.as_view(), 
        name="check"
    ),
    path(
        'pay/', 
        WalletPayView.as_view(), 
        name="pay-with-wallet"
    ),
    path(
        'transactions/', 
        TransactionListView.as_view(), 
        name="transactions"
    ),
]