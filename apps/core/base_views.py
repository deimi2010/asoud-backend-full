"""
Base view classes for consistent API structure and DRF Spectacular compatibility
"""
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema
from typing import Any, Dict, List, Optional
from utils.response import ApiResponse


class BaseAPIView(GenericAPIView):
    """
    Base API view with common functionality and DRF Spectacular compatibility
    """
    permission_classes = []
    
    def get_serializer_class(self):
        """
        Override this method to provide serializer class
        """
        return None
    
    def get_queryset(self):
        """
        Override this method to provide queryset
        """
        return None
    
    def success_response(self, data: Any = None, message: str = "Success", code: int = 200) -> Response:
        """
        Create a standardized success response
        """
        response_data = ApiResponse(
            success=True,
            code=code,
            data=data,
            message=message
        )
        return Response(response_data, status=code)
    
    def error_response(self, message: str = "Error", code: int = 400, error: str = None) -> Response:
        """
        Create a standardized error response
        """
        response_data = ApiResponse(
            success=False,
            code=code,
            error=error or message,
            message=message
        )
        return Response(response_data, status=code)


class BaseListView(BaseAPIView):
    """
    Base list view for listing objects
    """
    
    @extend_schema(
        summary="List objects",
        description="Retrieve a list of objects",
        responses={200: ApiResponse}
    )
    def get(self, request, *args, **kwargs):
        """
        List objects
        """
        try:
            queryset = self.get_queryset()
            if queryset is None:
                return self.error_response("Queryset not defined", 500)
            
            serializer_class = self.get_serializer_class()
            if serializer_class is None:
                return self.error_response("Serializer not defined", 500)
            
            serializer = serializer_class(queryset, many=True, context={"request": request})
            return self.success_response(data=serializer.data, message="Data retrieved successfully")
        
        except Exception as e:
            return self.error_response(f"Error retrieving data: {str(e)}", 500)


class BaseDetailView(BaseAPIView):
    """
    Base detail view for retrieving single objects
    """
    
    @extend_schema(
        summary="Retrieve object",
        description="Retrieve a single object by ID",
        responses={200: ApiResponse, 404: ApiResponse}
    )
    def get(self, request, pk, *args, **kwargs):
        """
        Retrieve object by ID
        """
        try:
            queryset = self.get_queryset()
            if queryset is None:
                return self.error_response("Queryset not defined", 500)
            
            serializer_class = self.get_serializer_class()
            if serializer_class is None:
                return self.error_response("Serializer not defined", 500)
            
            try:
                obj = queryset.get(pk=pk)
            except queryset.model.DoesNotExist:
                return self.error_response("Object not found", 404)
            
            serializer = serializer_class(obj, context={"request": request})
            return self.success_response(data=serializer.data, message="Data retrieved successfully")
        
        except Exception as e:
            return self.error_response(f"Error retrieving data: {str(e)}", 500)


class BaseCreateView(BaseAPIView):
    """
    Base create view for creating objects
    """
    
    @extend_schema(
        summary="Create object",
        description="Create a new object",
        request=None,  # Will be defined by serializer
        responses={201: ApiResponse, 400: ApiResponse}
    )
    def post(self, request, *args, **kwargs):
        """
        Create object
        """
        try:
            serializer_class = self.get_serializer_class()
            if serializer_class is None:
                return self.error_response("Serializer not defined", 500)
            
            serializer = serializer_class(data=request.data, context={"request": request})
            if serializer.is_valid():
                serializer.save()
                return self.success_response(data=serializer.data, message="Object created successfully", code=201)
            else:
                return self.error_response("Validation error", 400, str(serializer.errors))
        
        except Exception as e:
            return self.error_response(f"Error creating object: {str(e)}", 500)


class BaseUpdateView(BaseAPIView):
    """
    Base update view for updating objects
    """
    
    @extend_schema(
        summary="Update object",
        description="Update an existing object by ID",
        request=None,  # Will be defined by serializer
        responses={200: ApiResponse, 400: ApiResponse, 404: ApiResponse}
    )
    def put(self, request, pk, *args, **kwargs):
        """
        Update object by ID
        """
        try:
            queryset = self.get_queryset()
            if queryset is None:
                return self.error_response("Queryset not defined", 500)
            
            serializer_class = self.get_serializer_class()
            if serializer_class is None:
                return self.error_response("Serializer not defined", 500)
            
            try:
                obj = queryset.get(pk=pk)
            except queryset.model.DoesNotExist:
                return self.error_response("Object not found", 404)
            
            serializer = serializer_class(obj, data=request.data, context={"request": request})
            if serializer.is_valid():
                serializer.save()
                return self.success_response(data=serializer.data, message="Object updated successfully")
            else:
                return self.error_response("Validation error", 400, str(serializer.errors))
        
        except Exception as e:
            return self.error_response(f"Error updating object: {str(e)}", 500)


class BaseDeleteView(BaseAPIView):
    """
    Base delete view for deleting objects
    """
    
    @extend_schema(
        summary="Delete object",
        description="Delete an object by ID",
        responses={200: ApiResponse, 404: ApiResponse}
    )
    def delete(self, request, pk, *args, **kwargs):
        """
        Delete object by ID
        """
        try:
            queryset = self.get_queryset()
            if queryset is None:
                return self.error_response("Queryset not defined", 500)
            
            try:
                obj = queryset.get(pk=pk)
                obj.delete()
                return self.success_response(message="Object deleted successfully")
            except queryset.model.DoesNotExist:
                return self.error_response("Object not found", 404)
        
        except Exception as e:
            return self.error_response(f"Error deleting object: {str(e)}", 500)


