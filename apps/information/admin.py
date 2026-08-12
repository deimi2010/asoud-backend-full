from apps.base.admin import admin, BaseAdmin

from .models import Term, VoiceGuide

# Register your models here.


class TermAdmin(BaseAdmin):
    list_display = [
        'title',
        'content',
    ]

    fields = (
        'title',
        'content',
    ) + BaseAdmin.fields

    readonly_fields = BaseAdmin.readonly_fields


admin.site.register(Term, TermAdmin)


class VoiceGuideAdmin(BaseAdmin):
    list_display = [
        'market_file',
        'product_file',
    ]

    fields = (
        'market_file',
        'product_file',
    ) + BaseAdmin.fields

    readonly_fields = BaseAdmin.readonly_fields


admin.site.register(VoiceGuide, VoiceGuideAdmin)
