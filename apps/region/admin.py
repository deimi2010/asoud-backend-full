from apps.base.admin import admin, BaseAdmin, BaseTabularInline

from .models import Country, Province, City

# Register your models here.


class CityTabularInline(BaseTabularInline):
    model = City

    fields = (
        'name',
    ) + BaseTabularInline.fields

    readonly_fields = BaseTabularInline.readonly_fields


class ProvinceAdmin(BaseAdmin):
    inlines = [
        CityTabularInline,
    ]

    list_display = [
        'name',
        'country',
    ]

    fields = (
        'country',
        'name',
    ) + BaseAdmin.fields

    readonly_fields = BaseAdmin.readonly_fields


admin.site.register(Province, ProvinceAdmin)


class CountryAdmin(BaseAdmin):
    list_display = [
        'name',
    ]

    fields = (
        'name',
    ) + BaseAdmin.fields

    readonly_fields = BaseAdmin.readonly_fields


admin.site.register(Country, CountryAdmin)
