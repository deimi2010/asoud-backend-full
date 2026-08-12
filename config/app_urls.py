from django.urls import path, include
from django.utils.translation import gettext_lazy as _


urlpatterns = [
    path(
        '',
        include('apps.flutter.urls'),
    ),

]