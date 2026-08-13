from django.urls import path
from apps.product.views.admin_views import (
    ProductRevisionDecisionAdminView,
    ProductRevisionListAdminView,
)

urlpatterns = [
    path('revisions/', ProductRevisionListAdminView.as_view()),
    path('revisions/<uuid:pk>/', ProductRevisionDecisionAdminView.as_view()),
]
