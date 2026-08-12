from django.contrib import admin
from apps.sms.models import (
    Line, Template, BulkSms, PatternSms
)
from apps.base.admin import BaseAdmin
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
    ]

    fields = (
        'template_id',
        'content',
        'variables',
        'estimated_cost',
        'is_active',
    ) + BaseAdmin.fields

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