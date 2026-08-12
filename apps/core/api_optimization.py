"""
API Response Optimization for ASOUD Platform
"""

import logging
import time
import hashlib
from typing import Dict, List, Any, Optional
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import QuerySet
from django.core.cache import cache
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from apps.core.caching import cache_manager, cache_result
from apps.core.performance import QueryProfiler

logger = logging.getLogger(__name__)

class OptimizedPagination(PageNumberPagination):
    """
    Optimized pagination with performance enhancements
    """
    
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    
    def get_paginated_response(self, data):
        """Get paginated response with metadata"""
        return Response({
            'results': data,
            'pagination': {
                'count': self.page.paginator.count,
                'total_pages': self.page.paginator.num_pages,
                'current_page': self.page.number,
                'has_next': self.page.has_next(),
                'has_previous': self.page.has_previous(),
                'next_page': self.page.next_page_number() if self.page.has_next() else None,
                'previous_page': self.page.previous_page_number() if self.page.has_previous() else None,
                'page_size': self.get_page_size(self.request),
            }
        })

class CursorPagination:
    """
    Cursor-based pagination for better performance
    """
    
    def __init__(self, page_size=20, ordering='-id'):
        self.page_size = page_size
        self.ordering = ordering
    
    def paginate_queryset(self, queryset, request):
        """Paginate queryset using cursor"""
        cursor = request.GET.get('cursor')
        
        if cursor:
            queryset = queryset.filter(id__lt=cursor)
        
        queryset = queryset.order_by(self.ordering)[:self.page_size + 1]
        
        has_next = len(queryset) > self.page_size
        if has_next:
            queryset = queryset[:self.page_size]
            next_cursor = queryset[-1].id
        else:
            next_cursor = None
        
        return {
            'results': queryset,
            'next_cursor': next_cursor,
            'has_next': has_next,
        }

class APIResponseOptimizer:
    """
    API response optimization utilities
    """
    
    @staticmethod
    def optimize_queryset(queryset, select_related=None, prefetch_related=None, only=None, defer=None):
        """Optimize queryset for better performance"""
        if select_related:
            queryset = queryset.select_related(*select_related)
        
        if prefetch_related:
            queryset = queryset.prefetch_related(*prefetch_related)
        
        if only:
            queryset = queryset.only(*only)
        
        if defer:
            queryset = queryset.defer(*defer)
        
        return queryset
    
    @staticmethod
    def create_optimized_response(data, status_code=status.HTTP_200_OK, metadata=None):
        """Create optimized API response"""
        response_data = {
            'success': True,
            'data': data,
            'timestamp': timezone.now().isoformat(),
        }
        
        if metadata:
            response_data['metadata'] = metadata
        
        return Response(response_data, status=status_code)
    
    @staticmethod
    def create_error_response(message, status_code=status.HTTP_400_BAD_REQUEST, details=None):
        """Create optimized error response"""
        response_data = {
            'success': False,
            'error': message,
            'timestamp': timezone.now().isoformat(),
        }
        
        if details:
            response_data['details'] = details
        
        return Response(response_data, status=status_code)
    
    @staticmethod
    def create_paginated_response(queryset, request, serializer_class, page_size=20):
        """Create paginated response with optimization"""
        with QueryProfiler():
            paginator = Paginator(queryset, page_size)
            page_number = request.GET.get('page', 1)
            page = paginator.get_page(page_number)
            
            serializer = serializer_class(page.object_list, many=True)
            
            return Response({
                'success': True,
                'results': serializer.data,
                'pagination': {
                    'count': paginator.count,
                    'total_pages': paginator.num_pages,
                    'current_page': page.number,
                    'has_next': page.has_next(),
                    'has_previous': page.has_previous(),
                    'next_page': page.next_page_number() if page.has_next() else None,
                    'previous_page': page.previous_page_number() if page.has_previous() else None,
                },
                'timestamp': timezone.now().isoformat(),
            })

class CachedAPIView(APIView):
    """
    Base API view with caching support
    """
    
    cache_timeout = 300  # 5 minutes
    cache_key_prefix = "api"
    
    def get_cache_key(self, request, *args, **kwargs):
        """Generate cache key for request"""
        key_data = f"{self.cache_key_prefix}:{request.path}:{request.GET.urlencode()}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get_cached_response(self, request, *args, **kwargs):
        """Get cached response if available"""
        cache_key = self.get_cache_key(request, *args, **kwargs)
        return cache_manager.get(cache_key)
    
    def set_cached_response(self, request, response_data, *args, **kwargs):
        """Set response in cache"""
        cache_key = self.get_cache_key(request, *args, **kwargs)
        cache_manager.set(cache_key, response_data, self.cache_timeout)
    
    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to add caching"""
        if request.method == 'GET':
            cached_response = self.get_cached_response(request, *args, **kwargs)
            if cached_response is not None:
                return Response(cached_response)
        
        response = super().dispatch(request, *args, **kwargs)
        
        if request.method == 'GET' and response.status_code == 200:
            self.set_cached_response(request, response.data, *args, **kwargs)
        
        return response

class OptimizedAPIView(APIView):
    """
    Base API view with performance optimizations
    """
    
    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to add performance monitoring"""
        with QueryProfiler():
            return super().dispatch(request, *args, **kwargs)
    
    def get_optimized_queryset(self, queryset):
        """Get optimized queryset"""
        return APIResponseOptimizer.optimize_queryset(queryset)
    
    def create_response(self, data, status_code=status.HTTP_200_OK, metadata=None):
        """Create optimized response"""
        return APIResponseOptimizer.create_optimized_response(data, status_code, metadata)
    
    def create_error_response(self, message, status_code=status.HTTP_400_BAD_REQUEST, details=None):
        """Create optimized error response"""
        return APIResponseOptimizer.create_error_response(message, status_code, details)

class BulkOperationMixin:
    """
    Mixin for bulk operations
    """
    
    def bulk_create(self, data_list, serializer_class):
        """Bulk create objects"""
        created_objects = []
        errors = []
        
        for data in data_list:
            serializer = serializer_class(data=data)
            if serializer.is_valid():
                created_objects.append(serializer.save())
            else:
                errors.append({
                    'data': data,
                    'errors': serializer.errors
                })
        
        return {
            'created': created_objects,
            'errors': errors,
            'total_created': len(created_objects),
            'total_errors': len(errors)
        }
    
    def bulk_update(self, objects_data, serializer_class):
        """Bulk update objects"""
        updated_objects = []
        errors = []
        
        for obj_data in objects_data:
            obj_id = obj_data.get('id')
            if not obj_id:
                errors.append({
                    'data': obj_data,
                    'errors': {'id': 'ID is required for update'}
                })
                continue
            
            try:
                obj = serializer_class.Meta.model.objects.get(id=obj_id)
                serializer = serializer_class(obj, data=obj_data)
                if serializer.is_valid():
                    updated_objects.append(serializer.save())
                else:
                    errors.append({
                        'data': obj_data,
                        'errors': serializer.errors
                    })
            except serializer_class.Meta.model.DoesNotExist:
                errors.append({
                    'data': obj_data,
                    'errors': {'id': 'Object not found'}
                })
        
        return {
            'updated': updated_objects,
            'errors': errors,
            'total_updated': len(updated_objects),
            'total_errors': len(errors)
        }
    
    def bulk_delete(self, object_ids, model_class):
        """Bulk delete objects"""
        deleted_count = 0
        errors = []
        
        for obj_id in object_ids:
            try:
                obj = model_class.objects.get(id=obj_id)
                obj.delete()
                deleted_count += 1
            except model_class.DoesNotExist:
                errors.append({
                    'id': obj_id,
                    'error': 'Object not found'
                })
        
        return {
            'deleted_count': deleted_count,
            'errors': errors,
            'total_deleted': deleted_count,
            'total_errors': len(errors)
        }

class SearchOptimizationMixin:
    """
    Mixin for search optimization
    """
    
    def get_search_queryset(self, queryset, search_term, search_fields):
        """Get optimized search queryset"""
        if not search_term:
            return queryset
        
        from django.db.models import Q
        
        search_query = Q()
        for field in search_fields:
            search_query |= Q(**{f"{field}__icontains": search_term})
        
        return queryset.filter(search_query)
    
    def get_filtered_queryset(self, queryset, filters):
        """Get filtered queryset with optimization"""
        if not filters:
            return queryset
        
        return queryset.filter(**filters)
    
    def get_ordered_queryset(self, queryset, ordering):
        """Get ordered queryset with optimization"""
        if not ordering:
            return queryset
        
        return queryset.order_by(*ordering)

class PerformanceMonitoringMixin:
    """
    Mixin for performance monitoring
    """
    
    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to add performance monitoring"""
        start_time = time.time()
        
        with QueryProfiler():
            response = super().dispatch(request, *args, **kwargs)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Log performance metrics
        logger.info(f"API {request.method} {request.path} executed in {execution_time:.3f}s")
        
        # Add performance headers
        if hasattr(response, 'data'):
            response['X-Execution-Time'] = f"{execution_time:.3f}s"
            response['X-Query-Count'] = str(QueryProfiler.get_query_count())
        
        return response

class CacheInvalidationMixin:
    """
    Mixin for cache invalidation
    """
    
    def invalidate_related_caches(self, instance):
        """Invalidate related caches when object is modified"""
        # Invalidate model-specific caches
        model_name = instance.__class__.__name__.lower()
        cache_manager.delete_pattern(f"{model_name}:*")
        
        # Invalidate related object caches
        if hasattr(instance, 'market'):
            cache_manager.delete_pattern(f"market:*")
        if hasattr(instance, 'user'):
            cache_manager.delete_pattern(f"user:*")
        if hasattr(instance, 'product'):
            cache_manager.delete_pattern(f"product:*")
    
    def post_save(self, instance, created):
        """Post-save signal handler"""
        self.invalidate_related_caches(instance)
    
    def post_delete(self, instance):
        """Post-delete signal handler"""
        self.invalidate_related_caches(instance)

# Utility functions
def optimize_api_response(data, include_metadata=True):
    """Optimize API response data"""
    if include_metadata:
        return {
            'success': True,
            'data': data,
            'timestamp': timezone.now().isoformat(),
            'version': '1.0'
        }
    return data

def create_bulk_response(created=None, updated=None, deleted=None, errors=None):
    """Create bulk operation response"""
    response = {
        'success': True,
        'timestamp': timezone.now().isoformat(),
    }
    
    if created is not None:
        response['created'] = created
    if updated is not None:
        response['updated'] = updated
    if deleted is not None:
        response['deleted'] = deleted
    if errors is not None:
        response['errors'] = errors
    
    return response

def create_search_response(results, total_count, page, page_size, search_term=None):
    """Create search response"""
    return {
        'success': True,
        'results': results,
        'total_count': total_count,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size,
        },
        'search_term': search_term,
        'timestamp': timezone.now().isoformat(),
    }

