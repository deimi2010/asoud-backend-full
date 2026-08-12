from apps.base.admin import admin, BaseTabularInline
from django.template.defaultfilters import date as admin_dateformat

from .models import User, UserProfile, UserDocument, BankInfo, UserBankInfo

# Register your models here.


class UserProfileTabularInline(BaseTabularInline):
    model = UserProfile

    fields = (
        'address',
        'national_code',
        'birth_date',
        'iban_number',
        'picture',
    )


class UserDocumentTabularInline(BaseTabularInline):
    model = UserDocument

    fields = (
        'file',
    )


class UserAdmin(admin.ModelAdmin):
    def custom_last_login(self, obj):
        return admin_dateformat(obj.last_login, 'Y-m-d H:i:s')

    def custom_date_joined(self, obj):
        return admin_dateformat(obj.date_joined, 'Y-m-d H:i:s')

    custom_last_login.short_description = 'Last Login'  # Change field name
    custom_date_joined.short_description = 'Date Joined'

    inlines = [
        UserProfileTabularInline,
        UserDocumentTabularInline,
    ]

    fields = (
        'mobile_number',
        'pin',
        'type',
        'first_name',
        'last_name',
        'id',
        'last_login',
        'date_joined',
    )

    readonly_fields = (
        'id',
        'last_login',
        'date_joined',
    )


admin.site.register(User, UserAdmin)

class BankInfoAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'logo')

class UserBankInfoAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'bank_info',
        'card_number'
    )
    readonly_fields = (
        'id',
        'user',
        'bank_info'
    )

admin.site.register(BankInfo, BankInfoAdmin)
admin.site.register(UserBankInfo, UserBankInfoAdmin)
