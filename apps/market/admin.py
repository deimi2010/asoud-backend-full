from apps.base.admin import admin, BaseAdmin, BaseTabularInline
from django.utils import timezone

from .models import (
    Market,
    MarketLocation,
    MarketContact,
    MarketSlider,
    MarketTheme,
    MarketReport,
    MarketBookmark,
    MarketLike,
    MarketView,
    MarketDiscount,
    MarketSchedule,
    MarketRevision,
    MarketGatewayConnection,
    MarketShippingMethod,
    MarketMembership,
    BusinessCardProfile,
    BusinessCardTariff,
)

# Register your models here.


@admin.register(BusinessCardProfile)
class BusinessCardProfileAdmin(BaseAdmin):
    list_display = ('market', 'status', 'is_paid', 'subscription_end_date')
    list_filter = ('status', 'is_paid')
    search_fields = ('market__name', 'market__business_id')
    fields = (
        'market', 'status', 'status_reason', 'is_paid',
        'subscription_start_date', 'subscription_end_date', 'subscription_days',
    ) + BaseAdmin.fields
    actions = ('publish_cards', 'request_card_edits', 'deactivate_cards')

    @admin.action(description='Publish selected paid business cards')
    def publish_cards(self, request, queryset):
        queryset.filter(is_paid=True).update(
            status=BusinessCardProfile.PUBLISHED,
            status_reason='',
        )

    @admin.action(description='Return selected business cards for editing')
    def request_card_edits(self, request, queryset):
        queryset.update(status=BusinessCardProfile.NEEDS_EDITING)

    @admin.action(description='Deactivate selected business cards')
    def deactivate_cards(self, request, queryset):
        queryset.update(status=BusinessCardProfile.INACTIVE)


@admin.register(BusinessCardTariff)
class BusinessCardTariffAdmin(BaseAdmin):
    list_display = ('title', 'amount', 'duration_days', 'is_active')
    list_filter = ('is_active',)


class MarketLocationTabularInline(BaseTabularInline):
    model = MarketLocation

    fields = (
        'city',
        'address',
        'zip_code',
        'latitude',
        'longitude',
    )


class MarketContactTabularInline(BaseTabularInline):
    model = MarketContact

    fields = (
        'first_mobile_number',
        'second_mobile_number',
        'telephone',
        'fax',
        'email',
        'website_url',
        'messenger_ids',
    )


class MarketSliderTabularInline(BaseTabularInline):
    model = MarketSlider
    extra = 1

    fields = (
        'image',
        'url',
    )


class MarketThemeTabularInline(BaseTabularInline):
    model = MarketTheme
    fields = (
        'color',
        'font',
        'font_color',
    )


class MarketGatewayConnectionTabularInline(BaseTabularInline):
    model = MarketGatewayConnection
    extra = 0
    fields = (
        'gateway_type',
        'status',
        'user_code',
    )


class MarketScheduleTabularInline(BaseTabularInline):
    model = MarketSchedule
    extra = 1

    fields = (
        'day_of_week',
        'start_time',
        'end_time',
    )


class MarketShippingMethodTabularInline(BaseTabularInline):
    model = MarketShippingMethod
    extra = 0
    fields = ('name', 'price', 'is_active')


class MarketAdmin(BaseAdmin):
    inlines = [
        MarketLocationTabularInline,
        MarketContactTabularInline,
        MarketSliderTabularInline,
        MarketThemeTabularInline,
        MarketGatewayConnectionTabularInline,
        MarketScheduleTabularInline,
        MarketShippingMethodTabularInline,
    ]

    list_display = [
        'name',
        'user',
        'sales_channel',
    ]

    fields = (
        'user',
        'type',
        'sales_channel',
        'status',
        'is_paid',
        'subscription_start_date',
        'subscription_end_date',
        'business_id',
        'name',
        'description',
        'national_code',
        'sub_category',
        'slogan',
        'logo_img',
        'background_img',
        'user_only_img',
    ) + BaseAdmin.fields

    readonly_fields = BaseAdmin.readonly_fields


admin.site.register(Market, MarketAdmin)


@admin.register(MarketRevision)
class MarketRevisionAdmin(BaseAdmin):
    list_display = ('market', 'status', 'created_by', 'reviewed_by', 'created_at')
    list_filter = ('status',)
    readonly_fields = BaseAdmin.readonly_fields + ('payload',)


class MarketReportAdmin(BaseAdmin):
    list_display = [
        'market',
    ]

    fields = (
        'market',
        'creator',
        'description',
        'status',
    ) + BaseAdmin.fields

    readonly_fields = BaseAdmin.readonly_fields


admin.site.register(MarketReport, MarketReportAdmin)


class MarketBookmarkAdmin(BaseAdmin):
    list_display = [
        'user',
        'market',
        'is_active',
    ]

    fields = (
        'user',
        'market',
        'is_active',
    ) + BaseAdmin.fields

    readonly_fields = BaseAdmin.readonly_fields


admin.site.register(MarketBookmark, MarketBookmarkAdmin)


class MarketLikeAdmin(BaseAdmin):
    list_display = [
        'user',
        'market',
        'is_active',
    ]

    fields = (
        'user',
        'market',
        'is_active',
    ) + BaseAdmin.fields

    readonly_fields = BaseAdmin.readonly_fields


admin.site.register(MarketLike, MarketLikeAdmin)


class MarketViewAdmin(BaseAdmin):
    list_display = [
        'user',
        'market',
    ]

    fields = (
        'user',
        'market',
    ) + BaseAdmin.fields

    readonly_fields = BaseAdmin.readonly_fields


admin.site.register(MarketView, MarketViewAdmin)


class MarketDiscountAdmin(BaseAdmin):
    list_display = [
        'code',
        'title',
    ]

    fields = (
        'market',
        'code',
        'title',
        'description',
        'percentage',
        'usage_count',
    ) + BaseAdmin.fields

    readonly_fields = BaseAdmin.readonly_fields


admin.site.register(MarketDiscount, MarketDiscountAdmin)


@admin.register(MarketMembership)
class MarketMembershipAdmin(BaseAdmin):
    list_display = ('market', 'user', 'role', 'status', 'is_active')
    list_filter = ('status', 'role', 'is_active')
    search_fields = ('market__name', 'user__mobile_number')
    actions = ('approve_memberships',)

    @admin.action(description='تأیید و فعال‌سازی همکاران انتخاب‌شده')
    def approve_memberships(self, request, queryset):
        queryset.filter(status=MarketMembership.ADMIN_REVIEW).update(
            status=MarketMembership.ACTIVE,
            is_active=True,
            approved_by=request.user,
            admin_approved_at=timezone.now(),
            review_note='',
        )
