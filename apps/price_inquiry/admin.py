from django.contrib import admin
from apps.price_inquiry.models import (
    Inquiry,
    InquiryImage,
    InquiryAnswer
)
# Register your models here.
class InquiryImageAdmin(admin.TabularInline):
    model = InquiryImage
    extra = 1

class InquiryAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'type',
        'amount',
        'expiry'
    ]
    list_filter = [
        'type',
        'send'
    ]
    search_fields = [
        'name',
        'technical_detail',
    ]
    inlines = [InquiryImageAdmin]

admin.site.register(Inquiry, InquiryAdmin)


class InquiryAnswerAdmin(admin.ModelAdmin):
    list_display = [
        'inquiry',
        'detail',
        'total'
    ]
    search_fields = [
        'detial'
    ]

admin.site.register(InquiryAnswer, InquiryAnswerAdmin)