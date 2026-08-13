import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('referral', '0002_initial'),
        ('market', '0003_business_id_unique'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MarketInviteLink',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, null=True, verbose_name='Updated at')),
                ('token', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('is_active', models.BooleanField(default=True)),
                ('expires_at', models.DateTimeField(blank=True, null=True)),
                ('use_count', models.PositiveBigIntegerField(default=0)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='market_invite_links', to=settings.AUTH_USER_MODEL)),
                ('market', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='invite_links', to='market.market')),
            ],
            options={
                'indexes': [models.Index(fields=['market', 'is_active'], name='invite_market_active_idx')],
            },
        ),
        migrations.AddField(
            model_name='referral',
            name='market',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='referrals', to='market.market', verbose_name='Market'),
        ),
        migrations.AddField(
            model_name='referral',
            name='invite_link',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='referrals', to='referral.marketinvitelink'),
        ),
    ]
