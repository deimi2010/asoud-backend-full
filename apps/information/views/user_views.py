from rest_framework import views
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from utils.response import ApiResponse

from apps.information.models import Term
from apps.information.serializers.user_serializers import TermListSerializer


class TermListAPIView(views.APIView):
    # Terms of service must be readable before login (signup flow shows them).
    permission_classes = [AllowAny]

    def get(self, request, format=None):
        try:
            term = Term.get_solo()
        except:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error="No Term Found"
            )
        )

        serializer = TermListSerializer(
            term,
            context={"request": request},
        )

        success_response = ApiResponse(
            success=True,
            code=200,
            data=serializer.data,
            message='Data retrieved successfully'
        )

        return Response(success_response)
