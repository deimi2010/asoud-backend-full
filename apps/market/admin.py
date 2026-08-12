from apps.base.admin import admin, BaseAdmin, BaseTabularInline

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
)

# Register your models here.


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


class MarketScheduleTabularInline(BaseTabularInline):
    model = MarketSchedule
    extra = 1

    fields = (
        'day_of_week',
        'start_time',
        'end_time',
    )


class MarketAdmin(BaseAdmin):
    inlines = [
        MarketLocationTabularInline,
        MarketContactTabularInline,
        MarketSliderTabularInline,
        MarketThemeTabularInline,
        MarketScheduleTabularInline,
    ]

    list_display = [
        'name',
        'user',
    ]

    fields = (
        'user',
        'type',
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
