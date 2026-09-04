# urls.py
from django.urls import path
from apps.comment.views import (
    CommentView, 
    CommentDetailView,
    ContentCommentsView,
    CommentUpdateView
)

urlpatterns = [
    path('create/', CommentView.as_view()),
    path('<uuid:pk>/', CommentDetailView.as_view()),
    path('update/<uuid:pk>/', CommentUpdateView.as_view()),
    path('comments/<str:content_type>/<str:object_id>/', ContentCommentsView.as_view()),
]
