from rest_framework import permissions, views, status
from rest_framework.response import Response
from apps.discount.models import Discount
from utils.response import ApiResponse
from django.db import transaction
from apps.discount.serializers.user import (
    DiscountValidateSerializer,
    DiscountValidateResponseSerializer
)
from django.utils import timezone
from django.db.models import Q
from apps.cart.models import Order


DISCOUNT_NOT_VALID = "Discount Code Not Valid"
DISCOUNT_LIMIT_REACHED = "Discount Code Limitation Reached"
DISCOUNT_EXPIRED = "Discount Code Expired"


class DiscountValidateView(views.APIView):
    serializer_class = DiscountValidateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """
        validate discount for users when finalizing cart 
        """

        serializer = DiscountValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            try:
                discount = Discount.objects.select_for_update().get(
                    code__iexact=serializer.validated_data['code'].strip(),
                    content_type=serializer.validated_data['content_type'],
                    object_id=serializer.validated_data['object_id']
                )
            except Discount.DoesNotExist:
                return Response(
                    ApiResponse(
                        success=False,
                        code=404,
                        error=DISCOUNT_NOT_VALID
                    ),
                    status=status.HTTP_404_NOT_FOUND
                )
            if (
                discount.limitation
                and discount.consumed + discount.reserved >= discount.limitation
            ):
                return Response(
                    ApiResponse(
                        success=False,
                        code=400,
                        error=DISCOUNT_LIMIT_REACHED
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if discount.expiry and discount.expiry < timezone.now():
                return Response(
                    ApiResponse(
                        success=False,
                        code=400,
                        error=DISCOUNT_EXPIRED
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )

            allowed_users = {str(value) for value in discount.users}
            if allowed_users and not {
                request.user.mobile_number,
                str(request.user.id),
            }.intersection(allowed_users):
                return Response(
                    ApiResponse(
                        success=False,
                        code=400,
                        error=DISCOUNT_NOT_VALID
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )

            previously_used = Order.objects.filter(
                user=request.user,
                discount=discount,
            ).filter(
                Q(is_paid=True)
                | Q(
                    inventory_status__in=(
                        Order.INVENTORY_RESERVED,
                        Order.INVENTORY_CONFIRMED,
                    )
                )
            ).exists()
            if previously_used:
                return Response(
                    ApiResponse(
                        success=False,
                        code=400,
                        error=DISCOUNT_NOT_VALID,
                    ),
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
        serialized_data = DiscountValidateResponseSerializer(discount)
        return Response(
            ApiResponse(
                success=True,
                code=200,
                data=serialized_data.data
            )
        )
        
