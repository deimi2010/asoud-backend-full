from apps.base.admin import admin, BaseAdmin

from apps.advertise.models import Advertisement, AdvImage
# Register your models here.

class AdvertisementAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'type',
        'price',
        'category'
    ]
    fields = (
        'type',
        'name',
        'description',
        'category',
        'city',
        'state',
        'email',
        'keywords',
    ) + BaseAdmin.fields


class AdvertiseImageAdmin(BaseAdmin):
    list_display = ('advertise', 'image')
    fields = ('advertise', 'image')
    readonly_fields = ('advertise', )


admin.site.register(Advertisement, AdvertisementAdmin)
admin.site.register(AdvImage, AdvertiseImageAdmin)