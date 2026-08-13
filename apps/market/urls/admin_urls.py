from django.urls import path

from apps.market.views.admin_views import (
    MarketPublicationAdminView,
    MarketRevisionDecisionAdminView,
    MarketRevisionListAdminView,
)


urlpatterns = [
    path('revisions/', MarketRevisionListAdminView.as_view(), name='revision-list'),
    path('revisions/<uuid:pk>/', MarketRevisionDecisionAdminView.as_view(), name='revision-decision'),
    path('publications/<uuid:market_id>/', MarketPublicationAdminView.as_view(), name='publication-decision'),
]
