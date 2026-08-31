from django.urls import path

from apps.reserve.views.user.service import (
    ServiceListView,
    SpecialistListView,
    ReserveTimeListView,
    DayOffListView,
    AvailabilityView,
)
from apps.reserve.views.user.reservation import(
    ReservationCreateView,
    ReservationDetailView,
    ReservationListView,
    ReservationCancelView,
    ReservationRescheduleView,
    ReservationTrackingDetailView,
)

app_name = 'reserve_user'

urlpatterns = [
    path('service/', ServiceListView.as_view(), name='list-services'),
    path('specialist/', SpecialistListView.as_view(), name='list-specialists'),
    path('reserve-time/', ReserveTimeListView.as_view(), name='list-reserve-times'),
    path('dayoff/', DayOffListView.as_view(), name='list-daysoff'),
    path('availability/', AvailabilityView.as_view(), name='availability'),

    path('reservation/create', ReservationCreateView.as_view(), name="reservation-create"),
    path('reservation/<uuid:pk>', ReservationDetailView.as_view(), name="reservation-detail"),
    path(
        'reservation/tracking/<str:tracking_code>',
        ReservationTrackingDetailView.as_view(),
        name='reservation-tracking-detail',
    ),
    path('reservation/<uuid:pk>/cancel', ReservationCancelView.as_view(), name="reservation-cancel"),
    path('reservation/<uuid:pk>/reschedule', ReservationRescheduleView.as_view(), name="reservation-reschedule"),
    path('reservation/', ReservationListView.as_view(), name="reservation-list"),
]
