from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cart', '0002_initial'),
        ('product', '0003_productdiscount_contract'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderitem',
            name='product_discount',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='order_items',
                to='product.productdiscount',
            ),
        ),
        migrations.AddField(
            model_name='orderitem',
            name='product_discount_percentage_snapshot',
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
