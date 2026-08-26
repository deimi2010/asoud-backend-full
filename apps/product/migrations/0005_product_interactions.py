import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('product', '0004_alter_product_shipping_policy'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductLike',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, blank=True, null=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, blank=True, null=True, verbose_name='Updated at')),
                ('is_active', models.BooleanField(default=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='liked_by', to='product.product')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='product_likes', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'product_like'},
        ),
        migrations.CreateModel(
            name='ProductBookmark',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, blank=True, null=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, blank=True, null=True, verbose_name='Updated at')),
                ('is_active', models.BooleanField(default=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bookmarked_by', to='product.product')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='product_bookmarks', to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'product_bookmark'},
        ),
        migrations.CreateModel(
            name='ProductReport',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, blank=True, null=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, blank=True, null=True, verbose_name='Updated at')),
                ('description', models.TextField()),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('in_progress', 'In progress'), ('completed', 'Completed')], default='draft', max_length=20)),
                ('creator', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='product_reports', to=settings.AUTH_USER_MODEL)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reports', to='product.product')),
            ],
            options={'db_table': 'product_report'},
        ),
        migrations.AddConstraint(
            model_name='productlike',
            constraint=models.UniqueConstraint(fields=('user', 'product'), name='uniq_product_like_user_product'),
        ),
        migrations.AddConstraint(
            model_name='productbookmark',
            constraint=models.UniqueConstraint(fields=('user', 'product'), name='uniq_product_bookmark_user_product'),
        ),
    ]
