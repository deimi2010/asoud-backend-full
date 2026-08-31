from django.contrib import admin
from apps.sms.models import (
    Line, Template, BulkSms, PatternSms, SmsTariff, SmsCampaign, SmsRecipient
)
from apps.base.admin import BaseAdmin
from django.utils import timezone
# Register your models here.


class LineAdmin(BaseAdmin):
    list_display = [
        'number',
        'is_active',
    ]

    fields = (
        'number',
        'estimated_cost',
        'is_active',
    ) + BaseAdmin.fields

admin.site.register(Line, LineAdmin)


class TemplateAdmin(BaseAdmin):
    list_display = [
        'template_id',
        'is_active',
        'approval_status',
        'is_public',
    ]

    fields = (
        'template_id',
        'content',
        'variables',
        'estimated_cost',
        'is_active',
        'owner',
        'title',
        'category',
        'approval_status',
        'is_public',
        'review_note',
        'reviewed_by',
        'reviewed_at',
    ) + BaseAdmin.fields
    actions = ('approve_templates', 'request_template_edits', 'reject_templates')

    @admin.action(description='تأیید متن‌های انتخاب‌شده')
    def approve_templates(self, request, queryset):
        template_ids = list(queryset.values_list('id', flat=True))
        queryset.update(
            approval_status='approved', reviewed_by=request.user,
            reviewed_at=timezone.now(), review_note='',
        )
        SmsCampaign.objects.filter(
            template_id__in=template_ids,
            status=SmsCampaign.WAITING_APPROVAL,
        ).update(status=SmsCampaign.READY_FOR_PAYMENT)

    @admin.action(description='نیازمند اصلاح')
    def request_template_edits(self, request, queryset):
        queryset.update(approval_status='needs_editing', reviewed_by=request.user, reviewed_at=timezone.now())

    @admin.action(description='رد متن‌های انتخاب‌شده')
    def reject_templates(self, request, queryset):
        queryset.update(approval_status='rejected', reviewed_by=request.user, reviewed_at=timezone.now())

admin.site.register(Template, TemplateAdmin)

class BulkSmsAdmin(BaseAdmin):
    list_display = [
        'content',
        'line',
        'to',
        'status'
    ]
    list_filter = [
        'status'
    ]
    fields = (
        'user',
        'content',
        'line',
        'to',
        'cost',
        'actual_cost',
        'message_ids',
        'packId',
    ) + BaseAdmin.fields

admin.site.register(BulkSms, BulkSmsAdmin)


class PatternSmsAdmin(BaseAdmin):
    list_display = [
        'template',
        'message_id',
    ]

    fields = (
        'user',
        'template',
        'to',
        'message_id',
        'cost',
        'actual_cost',
    ) + BaseAdmin.fields

admin.site.register(PatternSms, PatternSmsAdmin)


@admin.register(SmsTariff)
class SmsTariffAdmin(BaseAdmin):
    list_display = ('title', 'price_per_segment', 'effective_from', 'is_active')
    list_filter = ('is_active',)


class SmsRecipientInline(admin.TabularInline):
    model = SmsRecipient
    extra = 0
    readonly_fields = ('name', 'mobile_number', 'status', 'provider_message_id', 'actual_cost', 'error_message')


@admin.register(SmsCampaign)
class SmsCampaignAdmin(BaseAdmin):
    list_display = ('title', 'user', 'status', 'recipient_count', 'estimated_cost', 'created_at')
    list_filter = ('status',)
    search_fields = ('title', 'user__mobile_number', 'provider_pack_id')
    inlines = (SmsRecipientInline,)
