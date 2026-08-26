import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cart', '0003_orderitem_product_discount_snapshot'),
        ('market', '0004_marketshippingmethod'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='shipping_amount',
            field=models.DecimalField(decimal_places=3, default=0, max_digits=14),
        ),
        migrations.AddField(
            model_name='order',
            name='shipping_method',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='orders', to='market.marketshippingmethod'),
        ),
        migrations.AddField(
            model_name='order',
            name='shipping_method_name_snapshot',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
    ]
