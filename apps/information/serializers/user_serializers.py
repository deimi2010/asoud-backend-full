from rest_framework import serializers

from apps.information.models import Term


class TermListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Term
        fields = [
            'title',
            'content',
        ]
