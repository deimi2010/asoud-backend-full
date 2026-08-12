from apps.base.admin import admin, BaseAdmin

from .models import (
    Comment,
)

# Register your models here.


class CommentAdmin(BaseAdmin):
    # Display these fields in the comment list view
    list_display = (
        'content_object',
        'content_type',
        'creator',
        'content',
        'parent_comment',
        'created_at',
    )

    # Make content_object and creator clickable links
    list_display_links = (
        'content_object',
        'creator',
    )

    # Add filters for easier searching
    list_filter = (
        'content_type',
        'creator',
        'parent_comment',
    )

    # Searchable fields in the admin
    search_fields = (
        'content',
        'creator__username',

    )

    # Order by creation date
    ordering = (
        '-created_at',
    )

    # Define how nested comments (replies) appear in the admin interface
    def get_queryset(self, request):
        # Override get_queryset to prefetch related content objects for optimization
        queryset = super().get_queryset(request)
        return queryset.select_related('creator', 'parent_comment').prefetch_related('replies')


admin.site.register(Comment, CommentAdmin)
