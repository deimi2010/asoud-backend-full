from rest_framework import permissions, status, views
from rest_framework.response import Response

from apps.sms.models import Line, Template
from apps.sms.serializers.owner import LineListSerializer, TemplateListSerializer
from utils.response import ApiResponse


def sms_sending_unavailable_response():
    return Response(
        ApiResponse(
            success=False,
            code=503,
            error={
                'code': 'sms_billing_unavailable',
                'detail': 'SMS sending is disabled until billing is implemented.',
            },
        ),
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


class LineListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        lines = Line.objects.filter(is_active=True)
        return Response(
            ApiResponse(
                success=True,
                code=200,
                data=LineListSerializer(lines, many=True).data,
            )
        )


class TemplateListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        templates = Template.objects.filter(is_active=True)
        return Response(
            ApiResponse(
                success=True,
                code=200,
                data=TemplateListSerializer(templates, many=True).data,
            )
        )


class BulkSmsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        return sms_sending_unavailable_response()


class PatternSmsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        return sms_sending_unavailable_response()
