from django.contrib import admin
from apps.reserve.models import (
    Service,
    Specialist,
    ReserveTime,
    DayOff,
    Reservation,
    SpecialistTimeOff,
)
# Register your models here.

class ServiceAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'market',
        'duration_minutes',
        'payment_mode',
        'is_active',
    ]
    search_fields = [
        'name'
    ]

admin.site.register(Service, ServiceAdmin)


class SpecialistAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'field',
        'market',
        'is_active',
    ]
    search_fields = [
        'user',
        'field'
    ]

admin.site.register(Specialist, SpecialistAdmin)


class ReserveTimeAdmin(admin.ModelAdmin):
    list_display = [
        'service',
        'day',
        'start',
        'end',
    ]
    search_fields = [
        'day',
        'start'
    ]

admin.site.register(ReserveTime, ReserveTimeAdmin)


class DayOffAdmin(admin.ModelAdmin):
    list_display = [
        'date',
        'market',
    ]
    search_fields = [
        'date'
    ]

admin.site.register(DayOff, DayOffAdmin)


class ReservationAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'tracking_code',
        'service',
        'specialist',
        'scheduled_start',
        'status',
        'is_paid'
    ]
    list_filter=[
        'is_paid', 'status',
    ]
    search_fields = [
        'specialist__user',
        'tracking_code',
        'service_name_snapshot',
    ]

admin.site.register(Reservation, ReservationAdmin)


@admin.register(SpecialistTimeOff)
class SpecialistTimeOffAdmin(admin.ModelAdmin):
    list_display = ('specialist', 'date', 'start', 'end', 'reason')
    list_filter = ('date',)
