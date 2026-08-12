from django.urls import path

from apps.sms.views.admin import (
    LineCreateView, 
    LineListView, 
    LineUpdateView,
    LineDeleteView, 
    TemplateCreateView,
    TemplateListView,
    TemplateUpdateView,
    TemplateDeleteView,
    BulkSmsDetailView,
    BulkSmsListView,
    BulkSmsUpdateView,
    PatternSmsDetailView,
    PatternSmsListView
)

app_name = 'sms_admin'

urlpatterns = [
    path('line/create', LineCreateView.as_view()),
    path('line/update/<str:pk>', LineUpdateView.as_view()),
    path('line/delete/<str:pk>', LineDeleteView.as_view()),
    path('line', LineListView.as_view()),

    path('template/create', TemplateCreateView.as_view()),
    path('template/update/<str:pk>', TemplateUpdateView.as_view()),
    path('template/delete/<str:pk>', TemplateDeleteView.as_view()),
    path('template', TemplateListView.as_view()),

    
    path('bulk', BulkSmsListView.as_view()),
    path('bulk/update/<str:pk>', BulkSmsUpdateView.as_view()),
    path('bulk/<str:pk>', BulkSmsDetailView.as_view()),

    path('pattern', PatternSmsListView.as_view()),
    path('pattern/<str:pk>', PatternSmsDetailView.as_view()),
]
