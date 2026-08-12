from collections import defaultdict
from uuid import UUID

from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.shortcuts import get_current_site
from django.db import models, transaction
from django_comments_xtd.models import XtdComment
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.comment.serializers import CommentSerializer, CommentUpdateSerializer
from apps.market.models import Market
from apps.product.models import Product


COMMENT_TARGETS = {'market': Market, 'product': Product}
PUBLIC_ROOT_LIMIT = 100


def _resolve_target(content_type, object_id):
    model = COMMENT_TARGETS.get(content_type)
    if model is None:
        raise serializers.ValidationError({'content_type': 'Unsupported content type.'})
    try:
        object_id = UUID(str(object_id))
    except (TypeError, ValueError) as exc:
        raise serializers.ValidationError({'object_id': 'Invalid object ID.'}) from exc
    filters = {'id': object_id, 'status': model.PUBLISHED}
    if model is Product:
        filters['market__status'] = Market.PUBLISHED
    try:
        target = model.objects.get(**filters)
    except model.DoesNotExist as exc:
        raise serializers.ValidationError({'object_id': 'Published target not found.'}) from exc
    return ContentType.objects.get_for_model(model), target


def _comment_target_is_public(comment):
    try:
        _resolve_target(comment.content_type.model, comment.object_pk)
    except serializers.ValidationError:
        return False
    return True


class CommentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        content_type, target = _resolve_target(
            request.data.get('content_type'),
            request.data.get('object_id'),
        )
        content_serializer = CommentUpdateSerializer(
            data={'comment': request.data.get('comment')}
        )
        content_serializer.is_valid(raise_exception=True)
        parent_id = request.data.get('parent_id') or 0
        site_id = get_current_site(request).id
        if parent_id:
            try:
                parent_id = int(parent_id)
                XtdComment.objects.get(
                    id=parent_id,
                    content_type=content_type,
                    object_pk=str(target.id),
                    site_id=site_id,
                    parent_id=models.F('id'),
                    is_public=True,
                    is_removed=False,
                )
            except (TypeError, ValueError, XtdComment.DoesNotExist):
                return Response(
                    {'error': 'Parent comment does not belong to this target'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        comment = XtdComment.objects.create(
            content_type=content_type,
            object_pk=str(target.id),
            user=request.user,
            comment=content_serializer.validated_data['comment'],
            parent_id=parent_id,
            site_id=site_id,
        )
        return Response(
            {'message': 'Comment created', 'id': comment.id},
            status=status.HTTP_201_CREATED,
        )


class CommentDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        try:
            comment = XtdComment.objects.get(
                id=pk,
                site_id=get_current_site(request).id,
                is_public=True,
                is_removed=False,
            )
        except XtdComment.DoesNotExist:
            return Response({'error': 'Comment not found'}, status=status.HTTP_404_NOT_FOUND)
        if not _comment_target_is_public(comment):
            return Response({'error': 'Comment not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(CommentSerializer(comment, context={'depth': 1}).data)


class ContentCommentsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, content_type, object_id):
        content_type_obj, target = _resolve_target(content_type, object_id)
        site_id = get_current_site(request).id
        visible = XtdComment.objects.filter(
            content_type=content_type_obj,
            object_pk=str(target.id),
            site_id=site_id,
            is_public=True,
            is_removed=False,
        )
        root_ids = list(
            visible.filter(parent_id=models.F('id'))
            .order_by('-submit_date')
            .values_list('id', flat=True)[:PUBLIC_ROOT_LIMIT]
        )
        comments = list(
            visible.filter(models.Q(id__in=root_ids) | models.Q(parent_id__in=root_ids))
            .order_by('submit_date')
        )
        roots = []
        children_by_parent = defaultdict(list)
        for comment in comments:
            if comment.parent_id == comment.id:
                roots.append(comment)
            else:
                children_by_parent[comment.parent_id].append(comment)
        return Response(
            CommentSerializer(
                roots,
                many=True,
                context={
                    'depth': 1,
                    'children_by_parent': children_by_parent,
                },
            ).data
        )


class CommentUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def put(self, request, pk):
        try:
            comment = XtdComment.objects.select_for_update().get(
                id=pk,
                user=request.user,
                site_id=get_current_site(request).id,
                is_public=True,
                is_removed=False,
            )
        except XtdComment.DoesNotExist:
            return Response({'error': 'Comment not found'}, status=status.HTTP_404_NOT_FOUND)
        if not _comment_target_is_public(comment):
            return Response({'error': 'Comment not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = CommentUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment.comment = serializer.validated_data['comment']
        comment.save(update_fields=['comment'])
        return Response(CommentSerializer(comment, context={'depth': 1}).data)
