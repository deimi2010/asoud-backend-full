from django_comments_xtd.models import XtdComment
from rest_framework import serializers


class CommentSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()

    class Meta:
        model = XtdComment
        fields = ['id', 'user', 'comment', 'submit_date', 'parent_id', 'level', 'children']
        read_only_fields = fields

    def get_user(self, obj):
        return str(obj.user_id) if obj.user_id else None

    def get_children(self, obj):
        depth = self.context.get('depth', 1)
        if depth <= 0:
            return []
        children_by_parent = self.context.get('children_by_parent')
        if children_by_parent is not None:
            children = children_by_parent.get(obj.id, [])
        else:
            children = XtdComment.objects.filter(
                parent_id=obj.id,
                content_type_id=obj.content_type_id,
                object_pk=obj.object_pk,
                site_id=obj.site_id,
                is_public=True,
                is_removed=False,
            ).exclude(id=obj.id).order_by('submit_date')
        return CommentSerializer(
            children,
            many=True,
            context={
                'depth': depth - 1,
                'children_by_parent': children_by_parent,
            },
        ).data


class CommentUpdateSerializer(serializers.Serializer):
    comment = serializers.CharField(max_length=2000, trim_whitespace=True)

    def validate_comment(self, value):
        if not value:
            raise serializers.ValidationError('Comment cannot be empty.')
        return value
