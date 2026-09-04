import uuid

from django.db import migrations, models


def copy_xtd_comments(apps, schema_editor):
    connection = schema_editor.connection
    tables = set(connection.introspection.table_names())
    if not {'django_comments', 'django_comments_xtd_xtdcomment'} <= tables:
        return

    quote = connection.ops.quote_name
    with connection.cursor() as cursor:
        cursor.execute(
            f'SELECT c.id, c.content_type_id, c.object_pk, c.user_id, '
            f'c.comment, c.submit_date, c.is_public, c.is_removed, x.parent_id '
            f'FROM {quote("django_comments")} c '
            f'JOIN {quote("django_comments_xtd_xtdcomment")} x '
            f'ON x.comment_ptr_id = c.id'
        )
        rows = cursor.fetchall()

    Comment = apps.get_model('comment', 'Comment')
    alias = connection.alias
    old_to_new = {}
    created_dates = {}
    pending = []
    for row in rows:
        old_id, content_type_id, object_pk, user_id, content = row[:5]
        if not user_id:
            continue
        try:
            object_id = uuid.UUID(str(object_pk))
        except (TypeError, ValueError, AttributeError):
            continue
        new_id = uuid.uuid5(uuid.NAMESPACE_URL, f'asoud:xtd-comment:{old_id}')
        old_to_new[old_id] = new_id
        created_dates[new_id] = row[5]
        pending.append(Comment(
            id=new_id,
            content_type_id=content_type_id,
            object_id=object_id,
            creator_id=user_id,
            content=content,
            is_public=row[6],
            is_removed=row[7],
        ))

    Comment.objects.using(alias).bulk_create(pending, ignore_conflicts=True)
    for comment_id, created_at in created_dates.items():
        Comment.objects.using(alias).filter(id=comment_id).update(
            created_at=created_at,
            updated_at=created_at,
        )
    for row in rows:
        old_id, parent_id = row[0], row[8]
        if old_id in old_to_new and parent_id != old_id and parent_id in old_to_new:
            Comment.objects.using(alias).filter(id=old_to_new[old_id]).update(
                parent_comment_id=old_to_new[parent_id]
            )


class Migration(migrations.Migration):
    dependencies = [('comment', '0002_initial')]

    operations = [
        migrations.AddField(
            model_name='comment',
            name='is_public',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='comment',
            name='is_removed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddIndex(
            model_name='comment',
            index=models.Index(
                fields=[
                    'content_type', 'object_id', 'is_public', 'is_removed',
                    'parent_comment',
                ],
                name='comment_target_visible_idx',
            ),
        ),
        migrations.RunPython(copy_xtd_comments, migrations.RunPython.noop),
    ]
