import secrets
import string

from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from rest_framework import views, status, permissions
from rest_framework.response import Response
from apps.discount.models import Discount
from utils.response import ApiResponse
from apps.discount.serializers.owner import (
    DiscountCreateSerializer,
    DiscountDetailSerializer,
    DiscountListSerializer
)
from apps.market.models import Market
from apps.product.models import Product

class DiscountCreateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    @transaction.atomic
    def post(self, request):
        """
        create discount
        """

        serializer = DiscountCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get market or product object
        content_type = serializer.validated_data['content_type']
        object_id = serializer.validated_data['object_id']

        model_class = content_type.model_class()

        try:
            content_object = model_class.objects.get(id=object_id)
        except model_class.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error={
                        'code': 'not_found',
                        'detail': f'No {content_type.model} found with id {object_id}.',
                    }
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Authorize user
        is_owned = (
            isinstance(content_object, Market) and content_object.user_id == request.user.id
        ) or (
            isinstance(content_object, Product)
            and content_object.market.user_id == request.user.id
        )
        if not is_owned:
            return Response(
                ApiResponse(
                    success=False,
                    code=403,
                    error={
                        'code': 'permission_denied',
                        'detail': 'You do not have permission to create discount for this object',
                    }
                ),
                status=status.HTTP_403_FORBIDDEN
            )
        
        characters = string.ascii_uppercase + string.digits
        for _ in range(5):
            code = ''.join(secrets.choice(characters) for _ in range(10))
            try:
                with transaction.atomic():
                    discount = serializer.save(
                        code=code,
                        owner=request.user,
                    )
                break
            except IntegrityError:
                continue
        else:
            return Response(
                ApiResponse(success=False, code=503, error='Unable to allocate a discount code.'),
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        
        return Response(
            ApiResponse(
                success=True,
                code=201,
                data=DiscountDetailSerializer(discount).data
            ),
            status=status.HTTP_201_CREATED
        )

class DiscountDetailView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, pk):
        """
        get the details of a discount
        """
        try:
            discount = Discount.objects.get(id=pk)
        except Discount.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error={
                        'code': 'discount_not_found',
                        'detail': 'Discount not found',
                    }
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Ownership check
        if discount.owner != request.user:
            return Response(
                ApiResponse(
                    success=False,
                    code=403,
                    error={
                        'code': 'permission_denied',
                        'detail': 'You do not have permission to view this discount',
                    }
                ),
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = DiscountDetailSerializer(discount)

        return Response(
            ApiResponse(
                success=True,
                code=200,
                data=serializer.data
            ),
            status=status.HTTP_200_OK
        )

class DiscountListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """
        get the list of discounts created by user
        both product and market discounts are returned
        """
        discounts = Discount.objects.filter(owner=request.user)
        
        serializer = DiscountListSerializer(discounts, many=True)

        return Response(
            ApiResponse(
                success=True,
                code=200,
                data=serializer.data
            ),
            status=status.HTTP_200_OK
        )

class DiscountDeleteView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def delete(self, request, pk):
        """
        delete discount with id
        """

        try:
            discount = Discount.objects.get(id=pk)
        except Discount.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error={
                        'code': 'discount_not_found',
                        'detail': 'Discount not found',
                    }
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Authorize user
        if discount.owner != request.user:
            return Response(
                ApiResponse(
                    success=False,
                    code=403,
                    error={
                        'code': 'permission_denied',
                        'detail': 'You do not have permission to delete this discount',
                    }
                ),
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            discount.delete()
        except ProtectedError:
            return Response(
                ApiResponse(
                    success=False,
                    code=409,
                    error='Discount is referenced by an order and cannot be deleted.',
                ),
                status=status.HTTP_409_CONFLICT,
            )
        return Response(
            ApiResponse(
                success=True,
                code=204
            ),
            status=status.HTTP_204_NO_CONTENT
        )
