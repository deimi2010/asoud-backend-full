import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('market', '0003_alter_marketslider_url'),
    ]

    operations = [
        migrations.CreateModel(
            name='MarketShippingMethod',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, null=True, verbose_name='Updated at')),
                ('name', models.CharField(max_length=64)),
                ('price', models.DecimalField(decimal_places=3, max_digits=14)),
                ('is_active', models.BooleanField(default=True)),
                ('market', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='shipping_methods', to='market.market')),
            ],
            options={
                'db_table': 'market_shipping_method',
                'ordering': ('created_at',),
            },
        ),
        migrations.AddConstraint(
            model_name='marketshippingmethod',
            constraint=models.UniqueConstraint(fields=('market', 'name'), name='uniq_market_shipping_method_name'),
        ),
        migrations.AddConstraint(
            model_name='marketshippingmethod',
            constraint=models.CheckConstraint(condition=models.Q(('price__gte', 0)), name='market_shipping_price_nonnegative'),
        ),
    ]
