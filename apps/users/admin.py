from apps.base.admin import admin, BaseTabularInline
from django.template.defaultfilters import date as admin_dateformat
from django.utils import timezone

from .models import User, UserProfile, UserDocument, BankInfo, UserBankInfo

# Register your models here.


class UserProfileTabularInline(BaseTabularInline):
    model = UserProfile
    fk_name = 'user'

    fields = (
        'address',
        'national_code',
        'birth_date',
        'iban_number',
        'picture',
        'status',
        'phone_ownership_status',
        'review_note',
    )


class UserDocumentTabularInline(BaseTabularInline):
    model = UserDocument
    fk_name = 'user'

    fields = (
        'document_type', 'file', 'status', 'review_note',
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


@admin.action(description='تأیید احراز هویت و تطبیق مالکیت شماره')
def approve_profiles(modeladmin, request, queryset):
    queryset.update(
        status=UserProfile.APPROVED,
        phone_ownership_status=UserProfile.PHONE_OWNER_MATCHED,
        reviewed_by=request.user,
        reviewed_at=timezone.now(),
        review_note='',
    )


@admin.register(UserProfile)
class UserProfileReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'national_code', 'status', 'phone_ownership_status', 'submitted_at')
    list_filter = ('status', 'phone_ownership_status')
    search_fields = ('user__mobile_number', 'national_code')
    actions = (approve_profiles,)


@admin.action(description='تأیید مدارک انتخاب‌شده')
def approve_documents(modeladmin, request, queryset):
    queryset.update(
        status=UserDocument.APPROVED,
        reviewed_by=request.user,
        reviewed_at=timezone.now(),
        review_note='',
    )


@admin.register(UserDocument)
class UserDocumentReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'document_type', 'status', 'created_at')
    list_filter = ('document_type', 'status')
    search_fields = ('user__mobile_number',)
    actions = (approve_documents,)
