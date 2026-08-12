import logging

from rest_framework import views, status, permissions
from rest_framework.response import Response
from django.shortcuts import redirect
from django.conf import settings
from utils.response import ApiResponse
from apps.payment.core import PaymentCore
from apps.payment.models import Payment, Zarinpal
from apps.payment.serializers.user import (
    PaymentCreateSerializer,
    PaymentSerializer,
    PaymentDetailSerializer
)

payment = PaymentCore()
logger = logging.getLogger(__name__)

# Create your views here.
class PaymentCreateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = PaymentCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        try:
            success, data = payment.pay(
                request.user,
                serializer.validated_data
            )

            if success:
                return Response(
                    ApiResponse(
                        success=True,
                        code=201,
                        data= {'id': str(data.id)}
                    ),
                    status=status.HTTP_201_CREATED
                )
            else:
                return Response(
                    ApiResponse(
                        success=False,
                        code=500,
                        error={
                            'code': 'payment_failed',
                            'detail': str(data),
                        }
                    ),
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        except Exception:
            logger.exception('Payment creation failed unexpectedly')
            return Response(
                ApiResponse(
                    success=False,
                    code=500,
                    error={
                        'code': 'internal_error',
                        'detail': 'Unable to create payment.',
                    }
                ),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class PaymentRedirectView(views.APIView):
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        zarinpal_id = request.GET.get('id')
        
        if not zarinpal_id:
            return Response(
                ApiResponse(
                    success=False,
                    code=400,
                    error={
                        'code': 'bad_request',
                        'detail': 'Missing zarinpal id parameter',
                    }
                ),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            zarinpal = Zarinpal.objects.select_related('payment').get(
                id=zarinpal_id,
                payment__status=Payment.PENDING,
            )
            if not zarinpal.authority:
                raise Zarinpal.DoesNotExist
            gateway_metadata = zarinpal.verification_data
            if (
                not isinstance(gateway_metadata, dict)
                or gateway_metadata.get('integrity_version') != payment.integrity_version
            ):
                raise Zarinpal.DoesNotExist
            gateway_subdomain = getattr(settings, 'ZARINPAL_URL', 'www')
            url = f'https://{gateway_subdomain}.zarinpal.com/pg/StartPay/{zarinpal.authority}'

            return redirect(url)
        
        except Zarinpal.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error={
                        'code': 'not_found',
                        'detail': 'Payment session not found',
                    }
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception:
            logger.exception('Payment redirect failed unexpectedly')
            return Response(
                ApiResponse(
                    success=False,
                    code=500,
                    error={
                        'code': 'internal_error',
                        'detail': 'Unable to open payment session.',
                    }
                ),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            ) 

class PaymentVerifyView(views.APIView):
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        try:
            success, data = payment.verify(request)
        except Exception:
            logger.exception('Payment verification failed unexpectedly')
            return Response(
                ApiResponse(
                    success=False,
                    code=500,
                    error={
                        'code': 'internal_error',
                        'detail': 'Unable to verify payment.',
                    },
                ),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        
        if success:
            return Response(
                ApiResponse(
                    success=True,
                    code=200,
                    message = data
                ),
                status=status.HTTP_200_OK
            )
        
        else:
            return Response(
                ApiResponse(
                    success=False,
                    code=400,
                    error={
                        'code': 'verification_failed',
                        'detail': data,
                    }
                ),
                status=status.HTTP_400_BAD_REQUEST
            )

class PaymentListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        payments = Payment.objects.filter(user=request.user)

        serializer = PaymentSerializer(payments, many=True)

        return Response(
            ApiResponse(
                success=True,
                code=200,
                data=serializer.data
            ),
            status=status.HTTP_200_OK
        )

class PaymentDetailView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, pk):
        try:
            payment = Payment.objects.get(id=pk)
        except Payment.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error={
                        'code': 'payment_not_found',
                        'detail': 'Payment not found',
                    }
                ),
                status=status.HTTP_404_NOT_FOUND
            )

        # Ownership check
        if payment.user != request.user:
            return Response(
                ApiResponse(
                    success=False,
                    code=403,
                    error={
                        'code': 'permission_denied',
                        'detail': 'You do not have permission to view this payment',
                    }
                ),
                status=status.HTTP_403_FORBIDDEN,
            )
        
        serializer = PaymentDetailSerializer(payment)

        return Response(
            ApiResponse(
                success=True,
                code=200,
                data=serializer.data
            ),
            status=status.HTTP_200_OK
        ) 
