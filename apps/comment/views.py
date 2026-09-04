from collections import defaultdict
from uuid import UUID

from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.comment.serializers import CommentSerializer, CommentUpdateSerializer
from apps.comment.models import Comment
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
        _resolve_target(comment.content_type.model, comment.object_id)
    except serializers.ValidationError:
        return False
    return True


class CommentView(APIView):
    serializer_class = CommentUpdateSerializer
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
        parent_id = request.data.get('parent_id')
        parent = None
        if parent_id:
            try:
                parent_id = UUID(str(parent_id))
                parent = Comment.objects.get(
                    id=parent_id,
                    content_type=content_type,
                    object_id=target.id,
                    parent_comment__isnull=True,
                    is_public=True,
                    is_removed=False,
                )
            except (TypeError, ValueError, Comment.DoesNotExist):
                return Response(
                    {'error': 'Parent comment does not belong to this target'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        comment = Comment.objects.create(
            content_type=content_type,
            object_id=target.id,
            creator=request.user,
            content=content_serializer.validated_data['comment'],
            parent_comment=parent,
        )
        return Response(
            {'message': 'Comment created', 'id': comment.id},
            status=status.HTTP_201_CREATED,
        )


class CommentDetailView(APIView):
    serializer_class = CommentSerializer
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        try:
            comment = Comment.objects.get(
                id=pk,
                is_public=True,
                is_removed=False,
            )
        except Comment.DoesNotExist:
            return Response({'error': 'Comment not found'}, status=status.HTTP_404_NOT_FOUND)
        if not _comment_target_is_public(comment):
            return Response({'error': 'Comment not found'}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            CommentSerializer(comment, context={'depth': 1, 'request': request}).data
        )


class ContentCommentsView(APIView):
    serializer_class = CommentSerializer
    permission_classes = [permissions.AllowAny]

    def get(self, request, content_type, object_id):
        content_type_obj, target = _resolve_target(content_type, object_id)
        visible = Comment.objects.filter(
            content_type=content_type_obj,
            object_id=target.id,
            is_public=True,
            is_removed=False,
        )
        root_ids = list(
            visible.filter(parent_comment__isnull=True)
            .order_by('-created_at')
            .values_list('id', flat=True)[:PUBLIC_ROOT_LIMIT]
        )
        comments = list(
            visible.filter(
                models.Q(id__in=root_ids) | models.Q(parent_comment_id__in=root_ids)
            )
            .select_related('creator', 'creator__userprofile')
            .order_by('created_at')
        )
        roots = []
        children_by_parent = defaultdict(list)
        for comment in comments:
            if comment.parent_comment_id is None:
                roots.append(comment)
            else:
                children_by_parent[comment.parent_comment_id].append(comment)
        return Response(
            CommentSerializer(
                roots,
                many=True,
                context={
                    'depth': 1,
                    'children_by_parent': children_by_parent,
                    'request': request,
                },
            ).data
        )


class CommentUpdateView(APIView):
    serializer_class = CommentUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def put(self, request, pk):
        try:
            comment = Comment.objects.select_for_update().get(
                id=pk,
                creator=request.user,
                is_public=True,
                is_removed=False,
            )
        except Comment.DoesNotExist:
            return Response({'error': 'Comment not found'}, status=status.HTTP_404_NOT_FOUND)
        if not _comment_target_is_public(comment):
            return Response({'error': 'Comment not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = CommentUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment.content = serializer.validated_data['comment']
        comment.save(update_fields=['content', 'updated_at'])
        return Response(
            CommentSerializer(comment, context={'depth': 1, 'request': request}).data
        )
