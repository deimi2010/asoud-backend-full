from apps.base.admin import admin, BaseAdmin

from .models import Gateway

# Register your models here.


class GatewayAdmin(BaseAdmin):
    list_display = [
        'content_type',
        'invoice_number',
        'amount',
        'status',
    ]

    fields = (
        'related_object_display',
        'invoice_number',
        'amount',
        'status',
        'reference_number',
        'track_id',
    ) + BaseAdmin.fields

    readonly_fields = (
        'related_object_display',
        'invoice_number',
        'amount',
        'status',
        'reference_number',
        'track_id',
    ) + BaseAdmin.readonly_fields

    def related_object_display(self, obj):
        if obj.related_object:
            return f"{obj.related_object} ({obj.content_type})"
        return "No related object"


admin.site.register(Gateway, GatewayAdmin)
