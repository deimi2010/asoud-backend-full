from rest_framework import views, status, permissions
from rest_framework.response import Response
from django.utils.translation import gettext_lazy as _

from utils.response import ApiResponse

from apps.market.models import (
    Market,
    MarketLocation,
    MarketContact,
    MarketSlider,
    MarketTheme,
)

from apps.market.serializers.owner_serializers import (
    MarketCreateSerializer,
    MarketUpdateSerializer,
    MarketLocationCreateSerializer,
    MarketLocationUpdateSerializer,
    MarketContactCreateSerializer,
    MarketContactUpdaterSerializer,
    MarketListSerializer,
    MarketSliderListSerializer,
    MarketThemeCreateSerializer,
)


class MarketCreateAPIView(views.APIView):
    """
    API view for creating new markets.
    
    This view allows authenticated users to create new markets
    with business information, category, and other details.
    
    Attributes:
        permission_classes: IsAuthenticated - Requires authentication
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        user = self.request.user

        serializer = MarketCreateSerializer(
            data=request.data,
            context={'request': request},
        )

        if serializer.is_valid(raise_exception=True):
            market = serializer.save(
                user=user,
            )

            market_id = market.id

            success_response = ApiResponse(
                success=True,
                code=200,
                data={
                    'market': market_id,
                    **serializer.data,
                },
                message='Market created successfully.',
            )

            return Response(success_response, status=status.HTTP_201_CREATED)


class MarketUpdateAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def put(self, request, pk):
        try:
            market = Market.objects.get(id=pk)

        except Market.DoesNotExist:
            response = ApiResponse(
                success=False,
                code=404,
                error={
                    'code': 'market_not_found',
                    'detail': 'Market not found in the database',
                }
            )
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        
        # Ownership check
        if market.user != request.user:
            response = ApiResponse(
                success=False,
                code=403,
                error={
                    'code': 'permission_denied',
                    'detail': 'You do not have permission to update this market',
                }
            )
            return Response(response, status=status.HTTP_403_FORBIDDEN)

        serializer = MarketUpdateSerializer(
            market,
            data=request.data,
            partial=False,
            context={'request': request},
        )

        if serializer.is_valid(raise_exception=True):
            market = serializer.save()

            success_response = ApiResponse(
                success=True,
                code=200,
                data=serializer.data,
                message='Market updated successfully.',
            )
            return Response(success_response, status=status.HTTP_200_OK)

class MarketGetAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, pk, format=None):
        try:
            market = Market.objects.get(id=pk)

        except Market.DoesNotExist:
            response = ApiResponse(
                success=False,
                code=404,
                error={
                    'code': 'market_not_found',
                    'detail': 'Market not found in the database',
                }
            )
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        
        # Ownership check
        if market.user != request.user:
            response = ApiResponse(
                success=False,
                code=403,
                error={
                    'code': 'permission_denied',
                    'detail': 'You do not have permission to view this market',
                }
            )
            return Response(response, status=status.HTTP_403_FORBIDDEN)

        serializer = MarketUpdateSerializer(
            market,
            context={'request': request},
        )

        success_response = ApiResponse(
            success=True,
            code=200,
            data=serializer.data,
            message='Data retrieved successfully.',
        )
        return Response(success_response, status=status.HTTP_200_OK)


class MarketListAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, format=None):
        user_obj = self.request.user

        market_list = Market.objects.filter(
            user=user_obj,
        )

        serializer = MarketListSerializer(
            market_list,
            many=True,
            context={"request": request},
        )

        success_response = ApiResponse(
            success=True,
            code=200,
            data=serializer.data,
            message='Data retrieved successfully'
        )

        return Response(success_response, status=status.HTTP_200_OK)


class MarketLocationCreateAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = MarketLocationCreateSerializer(
            data=request.data,
            context={'request': request},
        )

        if serializer.is_valid(raise_exception=True):
            # Ownership check
            market = serializer.validated_data.get('market')
            if market.user != request.user:
                return Response(
                    ApiResponse(
                        success=False,
                        code=403,
                        error={
                            'code': 'permission_denied',
                            'detail': 'You do not have permission to modify this market',
                        }
                    ),
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Prevent duplicate location for a market (OneToOne)
            if MarketLocation.objects.filter(market=market).exists():
                return Response(
                    ApiResponse(
                        success=False,
                        code=400,
                        error={
                            'code': 'location_exists',
                            'detail': 'Location for this market already exists',
                        }
                    ),
                    status=status.HTTP_400_BAD_REQUEST,
                )

            market_location = serializer.save()

            success_response = ApiResponse(
                success=True,
                code=201,
                data={
                    **serializer.data,
                },
                message='Market location created successfully.',
            )
            return Response(success_response, status=status.HTTP_201_CREATED)

        response = ApiResponse(
            success=False,
            code=500,
            error={
                'code': 'server_error',
                'detail': 'Server error',
            }
        )

        return Response(response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MarketLocationUpdateAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    def put(self, request, pk):
        try:
            market = Market.objects.get(id=pk)
            market_location = MarketLocation.objects.get(market=market)

        except Market.DoesNotExist:
            response = ApiResponse(
                success=False,
                code=404,
                error={
                    'code': 'market_not_found',
                    'detail': 'Market not found in the database',
                }
            )
            return Response(response, status=status.HTTP_404_NOT_FOUND)

        except MarketLocation.DoesNotExist:
            response = ApiResponse(
                success=False,
                code=404,
                error={
                    'code': 'market_location_not_found',
                    'detail': 'Market location not found in the database',
                }
            )
            return Response(response, status=status.HTTP_404_NOT_FOUND)

        # Ownership check
        if market.user != request.user:
            return Response(
                ApiResponse(
                    success=False,
                    code=403,
                    error={
                        'code': 'permission_denied',
                        'detail': 'You do not have permission to modify this market location',
                    }
                ),
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = MarketLocationUpdateSerializer(
            market_location,
            data=request.data,
            partial=False,
            context={'request': request},
        )

        if serializer.is_valid(raise_exception=True):
            serializer.save()

            success_response = ApiResponse(
                success=True,
                code=200,
                data=serializer.data,
                message='Market location updated successfully.',
            )
            return Response(success_response, status=status.HTTP_200_OK)

class MarketLocationGetAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request, pk, format=None):
        try:
            market = Market.objects.get(id=pk)
            market_location = MarketLocation.objects.get(market=market)

        except Market.DoesNotExist:
            response = ApiResponse(
                success=False,
                code=404,
                error={
                    'code': 'market_not_found',
                    'detail': 'Market not found in the database',
                }
            )
            return Response(response, status=status.HTTP_404_NOT_FOUND)

        except MarketLocation.DoesNotExist:
            response = ApiResponse(
                success=False,
                code=404,
                error={
                    'code': 'market_location_not_found',
                    'detail': 'Market location not found in the database',
                }
            )
            return Response(response, status=status.HTTP_404_NOT_FOUND)

        # Ownership check
        if market.user != request.user:
            return Response(
                ApiResponse(
                    success=False,
                    code=403,
                    error={
                        'code': 'permission_denied',
                        'detail': 'You do not have permission to view this market location',
                    }
                ),
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = MarketLocationUpdateSerializer(
            market_location,
            context={'request': request},
        )

        success_response = ApiResponse(
            success=True,
            code=200,
            data=serializer.data,
            message='Data retrieved successfully.',
        )
        return Response(success_response, status=status.HTTP_200_OK)


class MarketContactCreateAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = MarketContactCreateSerializer(
            data=request.data,
            context={'request': request},
        )
        
        if serializer.is_valid(raise_exception=True):
            # Ownership check
            market = serializer.validated_data.get('market')
            if market.user != request.user:
                return Response(
                    ApiResponse(
                        success=False,
                        code=403,
                        error={
                            'code': 'permission_denied',
                            'detail': 'You do not have permission to modify this market',
                        }
                    ),
                    status=status.HTTP_403_FORBIDDEN,
                )
            
            market_contact = serializer.save()

            success_response = ApiResponse(
                success=True,
                code=201,
                data={
                    **serializer.data,
                },
                message='Market contact created successfully.',
            )

            return Response(success_response, status=status.HTTP_201_CREATED)

        response = ApiResponse(
            success=False,
            code=500,
            error={
                'code': 'server_error',
                'detail': 'Server error',
            }
        )

        return Response(response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MarketContactUpdateAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def put(self, request, pk):
        try:
            market = Market.objects.get(id=pk)
            market_contact = MarketContact.objects.get(market=market)

        except Market.DoesNotExist:
            response = ApiResponse(
                success=False,
                code=404,
                error={
                    'code': 'market_not_found',
                    'detail': 'Market not found in the database',
                }
            )
            return Response(response, status=status.HTTP_404_NOT_FOUND)

        except MarketContact.DoesNotExist:
            response = ApiResponse(
                success=False,
                code=404,
                error={
                    'code': 'market_contact_not_found',
                    'detail': 'Market contact not found in the database',
                }
            )
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        
        # Ownership check
        if market.user != request.user:
            response = ApiResponse(
                success=False,
                code=403,
                error={
                    'code': 'permission_denied',
                    'detail': 'You do not have permission to update this market contact',
                }
            )
            return Response(response, status=status.HTTP_403_FORBIDDEN)

        serializer = MarketContactUpdaterSerializer(
            market_contact,
            data=request.data,
            partial=True,
            context={'request': request},
        )

        if serializer.is_valid(raise_exception=True):
            serializer.save()

            success_response = ApiResponse(
                success=True,
                code=200,
                data=serializer.data,
                message='Market contact updated successfully.',
            )
            return Response(success_response, status=status.HTTP_200_OK)

class MarketContactGetAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, pk, format=None):
        try:
            market = Market.objects.get(id=pk)
            market_contact = MarketContact.objects.get(market=market)

        except Market.DoesNotExist:
            response = ApiResponse(
                success=False,
                code=404,
                error={
                    'code': 'market_not_found',
                    'detail': 'Market not found in the database',
                }
            )
            return Response(response, status=status.HTTP_404_NOT_FOUND)

        except MarketContact.DoesNotExist:
            response = ApiResponse(
                success=False,
                code=404,
                error={
                    'code': 'market_contact_not_found',
                    'detail': 'Market contact not found in the database',
                }
            )
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        
        # Ownership check
        if market.user != request.user:
            response = ApiResponse(
                success=False,
                code=403,
                error={
                    'code': 'permission_denied',
                    'detail': 'You do not have permission to view this market contact',
                }
            )
            return Response(response, status=status.HTTP_403_FORBIDDEN)

        serializer = MarketContactUpdaterSerializer(
            market_contact,
            context={'request': request},
        )

        success_response = ApiResponse(
            success=True,
            code=200,
            data=serializer.data,
            message='Data retrieved successfully.',
        )
        return Response(success_response, status=status.HTTP_200_OK)


class MarketInactiveAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, pk, format=None):
        try:
            market_obj = Market.objects.get(id=pk)
        except Market.DoesNotExist:
            response = ApiResponse(
                success=False,
                code=404,
                error={
                    'code': 'market_not_found',
                    'detail': 'Market not found in the database',
                }
            )
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        
        # Ownership check
        if market_obj.user != request.user:
            return Response(
                ApiResponse(
                    success=False,
                    code=403,
                    error={
                        'code': 'permission_denied',
                        'detail': 'You do not have permission to modify this market',
                    }
                ),
                status=status.HTTP_403_FORBIDDEN
            )

        market_obj.status = "inactive"
        market_obj.save()

        success_response = ApiResponse(
            success=True,
            code=200,
            data={},
            message='Market inactivated successfully'
        )

        return Response(success_response, status=status.HTTP_200_OK)


class MarketQueueAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, pk, format=None):
        try:
            market_obj = Market.objects.get(id=pk)
        except Market.DoesNotExist:
            response = ApiResponse(
                success=False,
                code=404,
                error={
                    'code': 'market_not_found',
                    'detail': 'Market not found in the database',
                }
            )
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        
        # Ownership check
        if market_obj.user != request.user:
            return Response(
                ApiResponse(
                    success=False,
                    code=403,
                    error={
                        'code': 'permission_denied',
                        'detail': 'You do not have permission to modify this market',
                    }
                ),
                status=status.HTTP_403_FORBIDDEN
            )

        market_obj.status = "queue"
        market_obj.save()

        success_response = ApiResponse(
            success=True,
            code=200,
            data={},
            message='Market queued successfully'
        )

        return Response(success_response, status=status.HTTP_200_OK)


class MarketLogoAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, pk):
        logo_img = request.FILES.get('logo_img')

        try:
            market_obj = Market.objects.get(id=pk)
        except Market.DoesNotExist:
            response = ApiResponse(
                success=False,
                code=404,
                error={
                    'code': 'market_not_found',
                    'detail': 'Market not found in the database',
                }
            )
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        
        # Ownership check
        if market_obj.user != request.user:
            return Response(
                ApiResponse(
                    success=False,
                    code=403,
                    error={
                        'code': 'permission_denied',
                        'detail': 'You do not have permission to modify this market',
                    }
                ),
                status=status.HTTP_403_FORBIDDEN
            )

        market_obj.logo_img = logo_img
        market_obj.save()

        data = {
            'logo_img': request.build_absolute_uri(market_obj.logo_img.url),
        }

        success_response = ApiResponse(
            success=True,
            code=200,
            data=data,
            message='Logo modified successfully'
        )

        return Response(success_response, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        try:
            market_obj = Market.objects.get(id=pk)
        except Market.DoesNotExist:
            response = ApiResponse(
                success=False,
                code=404,
                error={
                    'code': 'market_not_found',
                    'detail': 'Market not found in the database',
                }
            )
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        
        # Ownership check
        if market_obj.user != request.user:
            return Response(
                ApiResponse(
                    success=False,
                    code=403,
                    error={
                        'code': 'permission_denied',
                        'detail': 'You do not have permission to modify this market',
                    }
                ),
                status=status.HTTP_403_FORBIDDEN
            )

        # Delete the logo_img file
        if market_obj.logo_img:
            market_obj.logo_img.delete(save=True)

        # Clear the reference to the logo_img in the model
        market_obj.logo_img = None
        market_obj.save()

        success_response = ApiResponse(
            success=True,
            code=200,
            data={},
            message='Logo removed successfully',
        )

        return Response(success_response, status=status.HTTP_200_OK)


class MarketBackgroundAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, pk):
        background_img = request.FILES.get('background_img')

        try:
            market_obj = Market.objects.get(id=pk)
        except Market.DoesNotExist:
            response = ApiResponse(
                success=False,
                code=404,
                error={
                    'code': 'market_not_found',
                    'detail': 'Market not found in the database',
                }
            )
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        
        # Ownership check
        if market_obj.user != request.user:
            return Response(
                ApiResponse(
                    success=False,
                    code=403,
                    error={
                        'code': 'permission_denied',
                        'detail': 'You do not have permission to modify this market',
                    }
                ),
                status=status.HTTP_403_FORBIDDEN
            )

        market_obj.background_img = background_img
        market_obj.save()

        data = {
            'background_img': request.build_absolute_uri(market_obj.background_img.url),
        }

        success_response = ApiResponse(
            success=True,
            code=200,
            data=data,
            message='Background modified successfully'
        )

        return Response(success_response, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        try:
            market_obj = Market.objects.get(id=pk)
        except Market.DoesNotExist:
            response = ApiResponse(
                success=False,
                code=404,
                error={
                    'code': 'market_not_found',
                    'detail': 'Market not found in the database',
                }
            )
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        
        # Ownership check
        if market_obj.user != request.user:
            return Response(
                ApiResponse(
                    success=False,
                    code=403,
                    error={
                        'code': 'permission_denied',
                        'detail': 'You do not have permission to modify this market',
                    }
                ),
                status=status.HTTP_403_FORBIDDEN
            )

        # Delete the logo_img file
        if market_obj.background_img:
            market_obj.background_img.delete(save=True)

        # Clear the reference to the logo_img in the model
        market_obj.background_img = None
        market_obj.save()

        success_response = ApiResponse(
            success=True,
            code=200,
            data={},
            message='Background removed successfully',
        )

        return Response(success_response, status=status.HTTP_200_OK)


class MarketSliderAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, pk):
        try:
            market_obj = Market.objects.get(id=pk)
        except Market.DoesNotExist:
            response = ApiResponse(
                success=False,
                code=404,
                error={
                    'code': 'market_not_found',
                    'detail': 'Market not found in the database',
                }
            )
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        
        # Ownership check
        if market_obj.user != request.user:
            return Response(
                ApiResponse(
                    success=False,
                    code=403,
                    error={
                        'code': 'permission_denied',
                        'detail': 'You do not have permission to view this market',
                    }
                ),
                status=status.HTTP_403_FORBIDDEN
            )

        slider_list = MarketSlider.objects.filter(market=market_obj)

        serializer = MarketSliderListSerializer(
            slider_list,
            many=True,
            context={"request": request},
        )

        success_response = ApiResponse(
            success=True,
            code=200,
            data=serializer.data,
            message='Data retrieved successfully'
        )

        return Response(success_response, status=status.HTTP_200_OK)

    def post(self, request, pk):
        slider_img = request.FILES.get('slider_img')

        try:
            market_obj = Market.objects.get(id=pk)
        except Market.DoesNotExist:
            response = ApiResponse(
                success=False,
                code=404,
                error={
                    'code': 'market_not_found',
                    'detail': 'Market not found in the database',
                }
            )
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        
        # Ownership check
        if market_obj.user != request.user:
            return Response(
                ApiResponse(
                    success=False,
                    code=403,
                    error={
                        'code': 'permission_denied',
                        'detail': 'You do not have permission to modify this market',
                    }
                ),
                status=status.HTTP_403_FORBIDDEN
            )

        market_slider_img = MarketSlider.objects.create(
            market=market_obj,
            image=slider_img,
        )

        data = {
            'slider_img': request.build_absolute_uri(market_slider_img.image.url),
        }

        success_response = ApiResponse(
            success=True,
            code=201,
            data=data,
            message='New slider has been created successfully'
        )

        return Response(success_response, status=status.HTTP_201_CREATED)

    def delete(self, request, pk):
        try:
            market_slider_obj = MarketSlider.objects.get(id=pk)
        except MarketSlider.DoesNotExist:
            response = ApiResponse(
                success=False,
                code=404,
                error={
                    'code': 'market_slider_not_found',
                    'detail': 'MarketSlider not found in the database',
                }
            )
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        
        # Ownership check
        if market_slider_obj.market.user != request.user:
            return Response(
                ApiResponse(
                    success=False,
                    code=403,
                    error={
                        'code': 'permission_denied',
                        'detail': 'You do not have permission to delete this slider',
                    }
                ),
                status=status.HTTP_403_FORBIDDEN
            )

        # Delete the file
        market_slider_obj.delete()

        success_response = ApiResponse(
            success=True,
            code=200,
            data={},
            message='Slider removed successfully',
        )

        return Response(success_response, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        try:
            market_slider_obj = MarketSlider.objects.get(id=pk)
        except MarketSlider.DoesNotExist:
            response = ApiResponse(
                success=False,
                code=404,
                error={
                    'code': 'market_slider_not_found',
                    'detail': 'MarketSlider not found in the database',
                }
            )
            return Response(response, status=status.HTTP_404_NOT_FOUND)
        
        # Ownership check
        if market_slider_obj.market.user != request.user:
            return Response(
                ApiResponse(
                    success=False,
                    code=403,
                    error={
                        'code': 'permission_denied',
                        'detail': 'You do not have permission to update this slider',
                    }
                ),
                status=status.HTTP_403_FORBIDDEN
            )

        # Update the image if provided in the request
        slider_img = request.FILES.get('slider_img')
        if slider_img:
            market_slider_obj.image = slider_img

        market_slider_obj.save()

        data = {
            'slider_img': request.build_absolute_uri(market_slider_obj.image.url),
        }

        success_response = ApiResponse(
            success=True,
            code=200,
            data=data,
            message='MarketSlider updated successfully'
        )

        return Response(success_response, status=status.HTTP_200_OK)


class MarketThemeAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, pk):
        try:
            market = Market.objects.get(id=pk)
        except Market.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error={
                        'code': 'market_not_found',
                        'detail': 'Market not found',
                    }
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Ownership check
        if market.user != request.user:
            return Response(
                ApiResponse(
                    success=False,
                    code=403,
                    error={
                        'code': 'permission_denied',
                        'detail': 'You do not have permission to modify this market',
                    }
                ),
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            market_theme = MarketTheme.objects.get(market=market)
            serializer = MarketThemeCreateSerializer(
                market_theme,
                data=request.data,
                context={'request': request},
            )
        except MarketTheme.DoesNotExist:
            serializer = MarketThemeCreateSerializer(
                data=request.data,
                context={'request': request},
            )

        if serializer.is_valid(raise_exception=True):
            serializer.save(market=market)

            success_response = ApiResponse(
                success=True,
                code=201,
                data={
                    **serializer.data,
                },
                message='Market theme created successfully.',
            )

            return Response(success_response, status=status.HTTP_201_CREATED)
