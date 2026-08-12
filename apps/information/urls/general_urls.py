from django.urls import path

from apps.information.views.user_views import TermListAPIView

app_name = 'information_general'

urlpatterns = [
    path(
        'term/',
        TermListAPIView.as_view(),
        name='term',
    ),
]
