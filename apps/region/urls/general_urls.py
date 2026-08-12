from django.urls import path

from apps.region.views.user_views import CountryListAPIView, ProvinceListAPIView, CityListAPIView

app_name = 'region_general'

urlpatterns = [
    path(
        'country/list/',
        CountryListAPIView.as_view(),
        name='country-list',
    ),
    # Province list (with optional country filter)
    path(
        'province/list/',
        ProvinceListAPIView.as_view(),
        name='province-list-all',
    ),
    path(
        'province/list/<str:pk>/',
        ProvinceListAPIView.as_view(),
        name='province-list',
    ),
    # City list (with optional province filter)
    path(
        'city/list/',
        CityListAPIView.as_view(),
        name='city-list-all',
    ),
    path(
        'city/list/<str:pk>/',
        CityListAPIView.as_view(),
        name='city-list',
    ),
]
