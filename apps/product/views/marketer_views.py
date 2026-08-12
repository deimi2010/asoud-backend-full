from rest_framework import views, status, permissions
from rest_framework.response import Response

from utils.response import ApiResponse

from apps.product.models import Product
from apps.product.serializers.marketer_serializers import (
    ProductListSerializer,
    ProductCreateSerializer,
)


class ProductListAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, pk):
        product_list = Product.objects.filter(
            is_marketer=True,
        ).select_related(
            'market',
            'sub_category',
            'theme'
        ).prefetch_related(
            'keywords',
            'images'
        )

        serializer = ProductListSerializer(
            product_list,
            many=True,
            context={"request": request},
        )

        success_response = ApiResponse(
            success=True,
            code=200,
            data=serializer.data,
            message='Data retrieved successfully'
        )

        return Response(success_response)


class ProductCreateAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ProductCreateSerializer(
            data=request.data,
            context={'request': request},
        )

        if serializer.is_valid(raise_exception=True):
            product = serializer.save()

            product_id = product.id

            success_response = ApiResponse(
                success=True,
                code=200,
                data={
                    'product': product_id,
                    **serializer.data,
                },
                message='Product created successfully.',
            )

            return Response(success_response, status=status.HTTP_201_CREATED)
