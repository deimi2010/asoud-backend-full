from django.urls import path

from apps.reserve.views.user.service import (
    ServiceListView,
    SpecialistListView,
    ReserveTimeListView,
    DayOffListView
)
from apps.reserve.views.user.reservation import(
    ReservationCreateView,
    ReservationDetailView,
    ReservationListView,
)

app_name = 'reserve_user'

urlpatterns = [
    path('service/', ServiceListView.as_view(), name='list-services'),
    path('specialist/', SpecialistListView.as_view(), name='list-specialists'),
    path('reserve-time/', ReserveTimeListView.as_view(), name='list-reserve-times'),
    path('dayoff/', DayOffListView.as_view(), name='list-daysoff'),

    path('reservation/create', ReservationCreateView.as_view(), name="reservation-create"),
    path('reservation/<uuid:pk>', ReservationDetailView.as_view(), name="reservation-detail"),
    path('reservation/', ReservationListView.as_view(), name="reservation-list"),
]
