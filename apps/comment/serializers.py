from django.core.exceptions import ObjectDoesNotExist
from django_comments_xtd.models import XtdComment
from rest_framework import serializers


class CommentSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    user_name = serializers.SerializerMethodField()
    user_image = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()

    class Meta:
        model = XtdComment
        fields = [
            'id', 'user', 'user_name', 'user_image', 'comment', 'submit_date',
            'parent_id', 'level', 'children',
        ]
        read_only_fields = fields

    def get_user(self, obj) -> str | None:
        return str(obj.user_id) if obj.user_id else None

    def get_user_name(self, obj) -> str:
        if not obj.user:
            return 'کاربر آسود'
        full_name = obj.user.get_full_name().strip()
        return full_name or 'کاربر آسود'

    def get_user_image(self, obj) -> str | None:
        if not obj.user:
            return None
        try:
            picture = obj.user.userprofile.picture
        except (AttributeError, ObjectDoesNotExist):
            return None
        if not picture:
            return None
        request = self.context.get('request')
        return request.build_absolute_uri(picture.url) if request else picture.url

    def get_children(self, obj) -> list[dict]:
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
                'request': self.context.get('request'),
            },
        ).data


class CommentUpdateSerializer(serializers.Serializer):
    comment = serializers.CharField(max_length=2000, trim_whitespace=True)

    def validate_comment(self, value):
        if not value:
            raise serializers.ValidationError('Comment cannot be empty.')
        return value
