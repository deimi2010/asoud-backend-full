from django.urls import path

from apps.reserve.views.owner.service import (
    ServiceCreateView,
    ServiceDetailView,
    ServiceListView,
    ServiceUpdateView,
    ServiceDeleteView
)
from apps.reserve.views.owner.specialist import (
    SpecialistCreateView,
    SpecialistDetailView,
    SpecialistListView,
    SpecialistUpdateView,
    SpecialistDeleteView
)
from apps.reserve.views.owner.reserve_time import (
    ReserveTimeCreateView,
    ReserveTimeDetailView,
    ReserveTimeListView,
    ReserveTimeUpdateView,
    ReserveTimeDeleteView
)
from apps.reserve.views.owner.day_off import (
    DayOffCreateView,
    DayOffListView,
    DayOffDeleteView,
)
from apps.reserve.views.owner.reservation import (
    ReservationDetailView,
    ReservationListView
)

app_name = 'reserve_owner'

urlpatterns = [
    path('service/',                ServiceListView.as_view(), name='service-list'),
    path('service/create',          ServiceCreateView.as_view(), name='service-create'),
    path('service/<uuid:pk>',        ServiceDetailView.as_view(), name='service-detail'),
    path('service/<uuid:pk>/update', ServiceUpdateView.as_view(), name='service-update'),
    path('service/<uuid:pk>/delete', ServiceDeleteView.as_view(), name='service-delete'),

    path('specialist/',                SpecialistListView.as_view(), name='specialist-list'),
    path('specialist/create',          SpecialistCreateView.as_view(), name='specialist-create'),
    path('specialist/<uuid:pk>',        SpecialistDetailView.as_view(), name='specialist-detail'),
    path('specialist/<uuid:pk>/update', SpecialistUpdateView.as_view(), name='specialist-update'),
    path('specialist/<uuid:pk>/delete', SpecialistDeleteView.as_view(), name='specialist-delete'),

    path('reserve-time/',                ReserveTimeListView.as_view(), name='reserve-time-list'),
    path('reserve-time/create',          ReserveTimeCreateView.as_view(), name='reserve-time-create'),
    path('reserve-time/<uuid:pk>',        ReserveTimeDetailView.as_view(), name='reserve-time-detail'),
    path('reserve-time/<uuid:pk>/update', ReserveTimeUpdateView.as_view(), name='reserve-time-update'),
    path('reserve-time/<uuid:pk>/delete', ReserveTimeDeleteView.as_view(), name='reserve-time-delete'),

    path('dayoff/',                DayOffListView.as_view(), name='dayoff-list'),
    path('dayoff/create',          DayOffCreateView.as_view(), name='dayoff-create'),
    path('dayoff/<uuid:pk>/delete', DayOffDeleteView.as_view(), name='dayoff-delete'),

    path('reservation/',            ReservationListView.as_view(), name='reservation-list'),
    path('reservation/<uuid:pk>',    ReservationDetailView.as_view(), name='reservation-detail'),
]
