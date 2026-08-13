from rest_framework import views, status, permissions
from rest_framework.response import Response
from utils.response import ApiResponse
from apps.wallet.models import Wallet, Transaction
from apps.wallet.serializer import (
    WalletCheckSerializer,
    TransactionSerializer,
    WalletPaySerializer,
    WalletSerializer
)
from apps.payment.core import PostPaymentCore
from drf_spectacular.utils import OpenApiResponse, extend_schema
# Create your views here.


class WalletBalanceView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(responses={200: WalletSerializer}, tags=['Wallet'])
    def get(self, request):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        
        serializer = WalletSerializer(wallet)
        return Response(
            ApiResponse(
                success=True,
                code=200,
                data=serializer.data
            ),
            status=status.HTTP_200_OK
        )
        
class WalletCheckView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(request=WalletCheckSerializer, responses={200: OpenApiResponse(description='Balance is sufficient')}, tags=['Wallet'])
    def post(self, request):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        
        serializer = WalletCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        amount = serializer.validated_data['amount']
        
        if wallet.balance >= amount:
            return Response(
                ApiResponse(
                    success=True,
                    code=200,
                    message="Sufficient Balance"
                ),
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                ApiResponse(
                    success=False,
                    code=400,
                    error={
                        'code': 'insufficient_balance',
                        'detail': 'Insufficient wallet balance',
                    }
                ),
                status=status.HTTP_400_BAD_REQUEST
            )

class WalletPayView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(request=WalletPaySerializer, responses={200: OpenApiResponse(description='Wallet payment completed')}, tags=['Wallet'])
    def post(self, request):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        
        serializer = WalletPaySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        post_payment = PostPaymentCore(request.user)
        success, result = post_payment.wallet_process(
                target=serializer.validated_data['target_content'],
                pk=serializer.validated_data['target_id'],
                amount=serializer.validated_data['amount'],
                wallet_id=wallet.id,
        )

        if success:
            return Response(
                ApiResponse(
                    success=True,
                    code=200,
                    message="payment successfull"
                ),
                status=status.HTTP_200_OK
            )
        return Response(
            ApiResponse(
                success=False,
                code=400,
                error={
                    'code': 'wallet_payment_failed',
                    'detail': str(result),
                }
            ),
            status=status.HTTP_400_BAD_REQUEST
        )

class TransactionListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(responses={200: TransactionSerializer(many=True)}, tags=['Wallet'])
    def get(self, request):
        transactions = Transaction.objects.filter(user=request.user)
        
        serializer = TransactionSerializer(transactions, many=True)
        return Response(
            ApiResponse(
                success=True,
                code=200,
                data=serializer.data
            ),
            status=status.HTTP_200_OK
        )
