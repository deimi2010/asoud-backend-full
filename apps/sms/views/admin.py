import logging

from apps.sms.models import BulkSms, PatternSms, Line, Template
from rest_framework import views, status, permissions
from rest_framework.response import Response
from utils.response import ApiResponse
from apps.sms.serializers.admin import (
    LineSerializer,
    TemplateSerializer,
    BulkSerializer,
    PatternSerializer
)


logger = logging.getLogger(__name__)


class LineCreateView(views.APIView):
    permission_classes = [permissions.IsAdminUser]
    
    def post(self, request):
        serializer = LineSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.save()

        return Response(
            ApiResponse(
                success=True,
                code=201,
                data=serializer.data
            )
        )


class LineUpdateView(views.APIView):
    permission_classes = [permissions.IsAdminUser]
    
    def put(self, request, pk=None):
        try:
            line = Line.objects.get(id=pk)
            serializer = LineSerializer(line, request.data, partial=True)
            serializer.is_valid(raise_exception=True)

            serializer.save()

            return Response(
                ApiResponse(
                    success=True,
                    code=201,
                    data=serializer.data
                )
            )
        except Line.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error="Line Not Found"
                ),
                status=status.HTTP_404_NOT_FOUND
            )
    

class LineListView(views.APIView):
    permission_classes = [permissions.IsAdminUser]
    
    def get(self, request):
        lines = Line.objects.all()
        serializer = LineSerializer(lines, many=True)

        return Response(
            ApiResponse(
                success=True,
                code=200,
                data=serializer.data
            )
        )

class LineDeleteView(views.APIView):
    permission_classes = [permissions.IsAdminUser]
    
    def delete(self, request, pk):
        try:
            line = Line.objects.get(id=pk)
        except Line.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error="Line Not Found"
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        
        line.delete()
        return Response(
            ApiResponse(
                success=True,
                code=204
            ),
            status=status.HTTP_204_NO_CONTENT
        )

class TemplateCreateView(views.APIView):
    permission_classes = [permissions.IsAdminUser]
    
    def post(self, request):
        serializer = TemplateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.save()

        return Response(
            ApiResponse(
                success=True,
                code=201,
                data=serializer.data
            )
        )
    
class TemplateListView(views.APIView):
    permission_classes = [permissions.IsAdminUser]
    
    def get(self, request):
        templates = Template.objects.all()
        serializer = TemplateSerializer(templates, many=True)

        return Response(
            ApiResponse(
                success=True,
                code=200,
                data=serializer.data
            )
        )

class TemplateUpdateView(views.APIView):
    permission_classes = [permissions.IsAdminUser]
    
    def put(self, request, pk):
        try:
            template = Template.objects.get(id=pk)
        except Template.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error="Template Not Found"
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = TemplateSerializer(template, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            ApiResponse(
                success=True,
                code=200,
                data=serializer.data
            )
        )

class TemplateDeleteView(views.APIView):
    permission_classes = [permissions.IsAdminUser]
    
    def delete(self, request, pk):
        try:
            template = Template.objects.get(id=pk)
        except Template.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error="Template Not Found"
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        
        template.delete()
        return Response(
            ApiResponse(
                success=True,
                code=200,
                message="Template Deleted Successfully"
            )
        )

class BulkSmsDetailView(views.APIView):
    permission_classes = [permissions.IsAdminUser]
    
    def get(self, request, pk):
        try:
            sms = BulkSms.objects.get(id=pk)
        except BulkSms.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error="SMS Not Found"
                )
            )
        
        serializer = BulkSerializer(sms)
        
        return Response(
            ApiResponse(
                success=True,
                code=200,
                data=serializer.data
            )
        )

class BulkSmsListView(views.APIView):
    permission_classes = [permissions.IsAdminUser]
    
    def get(self, request):
        sms = BulkSms.objects.all()
        serializer = BulkSerializer(sms, many=True)
        
        return Response(
            ApiResponse(
                success=True,
                code=200,
                data=serializer.data
            )
        )
    
class BulkSmsUpdateView(views.APIView):
    permission_classes = [permissions.IsAdminUser]
    
    def put(self, request, pk):
        return Response(
            ApiResponse(
                success=False,
                code=503,
                error='SMS sending is disabled until billing is implemented.',
            ),
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class PatternSmsDetailView(views.APIView):
    permission_classes = [permissions.IsAdminUser]
    
    def get(self, request, pk):
        try:
            sms = PatternSms.objects.get(id=pk)
        except PatternSms.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error="SMS Not Found"
                )
            )
        
        serializer = PatternSerializer(sms)
        
        return Response(
            ApiResponse(
                success=True,
                code=200,
                data=serializer.data
            )
        )

class PatternSmsListView(views.APIView):
    permission_classes = [permissions.IsAdminUser]
    
    def get(self, request):
        sms = PatternSms.objects.all()
        serializer = PatternSerializer(sms, many=True)
        
        return Response(
            ApiResponse(
                success=True,
                code=200,
                data=serializer.data
            )
        )
