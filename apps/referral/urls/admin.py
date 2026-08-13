from django.urls import path

from apps.referral.admin_views import (
    ReferralCommissionAdminView,
    ReferralCommissionStatusAdminView,
    ReferralLevelListAdminView,
    ReferralLevelUpdateAdminView,
)


urlpatterns = [
    path('levels/', ReferralLevelListAdminView.as_view(), name='level-list'),
    path('levels/<int:level>/', ReferralLevelUpdateAdminView.as_view(), name='level-update'),
    path('commissions/', ReferralCommissionAdminView.as_view(), name='commission-list'),
    path('commissions/<uuid:pk>/status/', ReferralCommissionStatusAdminView.as_view(), name='commission-status'),
]
