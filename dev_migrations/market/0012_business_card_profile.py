import django.db.models.deletion
import uuid
from django.db import migrations, models


def create_cards(apps, schema_editor):
    Market = apps.get_model('market', 'Market')
    Card = apps.get_model('market', 'BusinessCardProfile')
    alias = schema_editor.connection.alias
    Card.objects.using(alias).bulk_create(
        [Card(market_id=market_id) for market_id in Market.objects.using(alias).values_list('id', flat=True)],
        ignore_conflicts=True,
    )


class Migration(migrations.Migration):
    dependencies = [('market', '0011_market_sales_channel')]

    operations = [
        migrations.CreateModel(
            name='BusinessCardTariff',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, null=True, verbose_name='Updated at')),
                ('title', models.CharField(default='Business card subscription', max_length=100)),
                ('amount', models.DecimalField(decimal_places=3, max_digits=14)),
                ('duration_days', models.PositiveIntegerField(default=365)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
            ],
            options={'db_table': 'business_card_tariff', 'ordering': ('-created_at',)},
        ),
        migrations.CreateModel(
            name='BusinessCardProfile',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, null=True, verbose_name='Updated at')),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('queue', 'In queue'), ('published', 'Published'), ('needs_editing', 'Needs editing'), ('inactive', 'Inactive')], db_index=True, default='draft', max_length=20)),
                ('status_reason', models.TextField(blank=True, default='')),
                ('is_paid', models.BooleanField(default=False)),
                ('subscription_start_date', models.DateTimeField(blank=True, null=True)),
                ('subscription_end_date', models.DateTimeField(blank=True, null=True)),
                ('subscription_days', models.PositiveIntegerField(default=365)),
                ('market', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='business_card', to='market.market')),
            ],
            options={'db_table': 'business_card_profile', 'ordering': ('created_at', 'id')},
        ),
        migrations.RunPython(create_cards, migrations.RunPython.noop),
    ]
