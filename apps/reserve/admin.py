from django.contrib import admin
from apps.reserve.models import (
    Service,
    Specialist,
    ReserveTime,
    DayOff,
    Reservation
)
# Register your models here.

class ServiceAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'market',
    ]
    search_fields = [
        'name'
    ]

admin.site.register(Service, ServiceAdmin)


class SpecialistAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'field',
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
        'reserve',
        'specialist',
        'is_paid'
    ]
    list_filter=[
        'is_paid',
    ]
    search_fields = [
        'specialist',
    ]

admin.site.register(Reservation, ReservationAdmin)
