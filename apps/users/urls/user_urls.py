from django.urls import path

from apps.users.views.user_views import (
    PinCreateAPIView, PinVerifyAPIView,
    LogoutAPIView, WebSocketTicketAPIView,
    BankInfoCreateView, BankInfoUpdateView,
    BankInfoListView, BankInfoDeleteView,
    BankInfoDetailView, BanksListView)
from apps.users.views.user_views import SelfProfileView


app_name = 'users_user'

urlpatterns = [
    path('pin/create/', PinCreateAPIView.as_view(), name='pin-create'),
    path('pin/verify/', PinVerifyAPIView.as_view(), name='pin-verify'),
    path('logout/', LogoutAPIView.as_view(), name='logout'),
    path('ws-ticket/', WebSocketTicketAPIView.as_view(), name='ws-ticket'),
    path('profile/', SelfProfileView.as_view(), name='self-profile'),
    path('bank-info/list/', BanksListView.as_view(), name='banks-list'),
    path('bank/info/create/', BankInfoCreateView.as_view(), name= 'bank-create'),
    path('bank/info/list/', BankInfoListView.as_view(), name= 'bank-list'),
    path('bank/info/detail/<uuid:pk>/', BankInfoDetailView.as_view(), name= 'bank-detail'),
    path('bank/info/update/<uuid:pk>/', BankInfoUpdateView.as_view(), name= 'bank-update'),
    path('bank/info/delete/<uuid:pk>/', BankInfoDeleteView.as_view(), name= 'bank-delete')
]
