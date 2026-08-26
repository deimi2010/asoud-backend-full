import django.db.models.deletion
from django.db import migrations, models
from django.db.models import Count, Q


def release_duplicate_theme_slots(apps, schema_editor):
    Product = apps.get_model('product', 'Product')
    duplicates = (
        Product.objects.exclude(theme_id=None)
        .exclude(theme_index=None)
        .values('theme_id', 'theme_index')
        .annotate(total=Count('id'))
        .filter(total__gt=1)
    )
    for duplicate in duplicates.iterator():
        products = Product.objects.filter(
            theme_id=duplicate['theme_id'],
            theme_index=duplicate['theme_index'],
        ).order_by('created_at', 'id')
        products.exclude(id=products.values_list('id', flat=True).first()).update(
            theme_id=None,
            theme_index=None,
        )


class Migration(migrations.Migration):
    dependencies = [
        ('product', '0005_product_interactions'),
    ]

    operations = [
        migrations.AddField(
            model_name='producttheme',
            name='client_request_id',
            field=models.UUIDField(
                blank=True,
                editable=False,
                null=True,
                unique=True,
            ),
        ),
        migrations.AlterField(
            model_name='product',
            name='theme',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='products',
                to='product.producttheme',
                verbose_name='Theme',
            ),
        ),
        migrations.RunPython(
            release_duplicate_theme_slots,
            migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name='product',
            constraint=models.UniqueConstraint(
                condition=Q(theme__isnull=False, theme_index__isnull=False),
                fields=('theme', 'theme_index'),
                name='uniq_product_theme_slot',
            ),
        ),
    ]
