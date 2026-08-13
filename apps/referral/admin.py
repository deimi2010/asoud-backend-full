from apps.base.admin import BaseAdmin, admin

from apps.referral.models import (
    MarketInviteLink,
    Referral,
    ReferralCommission,
    ReferralLevel,
    SignupInviteIntent,
    StoreAccess,
)


admin.site.register(Referral, BaseAdmin)
admin.site.register(MarketInviteLink, BaseAdmin)
admin.site.register(StoreAccess, BaseAdmin)
admin.site.register(SignupInviteIntent, BaseAdmin)


@admin.register(ReferralLevel)
class ReferralLevelAdmin(BaseAdmin):
    list_display = ('level', 'percentage', 'is_active')
    list_editable = ('percentage', 'is_active')


@admin.register(ReferralCommission)
class ReferralCommissionAdmin(BaseAdmin):
    list_display = (
        'beneficiary', 'source_user', 'market', 'level', 'percentage', 'amount', 'status'
    )
    list_filter = ('level', 'status')
    readonly_fields = BaseAdmin.readonly_fields + (
        'payment', 'market', 'source_user', 'beneficiary', 'level',
        'base_amount', 'percentage', 'amount',
    )
