import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('market', '0003_business_id_unique'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MarketMembership',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, null=True, verbose_name='Updated at')),
                ('role', models.CharField(choices=[('manager', 'Manager'), ('editor', 'Editor'), ('viewer', 'Viewer')], default='editor', max_length=16)),
                ('is_active', models.BooleanField(default=True)),
                ('market', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to='market.market')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='market_memberships', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'market_membership',
                'indexes': [models.Index(fields=['user', 'is_active'], name='market_member_active_idx')],
                'constraints': [models.UniqueConstraint(fields=('market', 'user'), name='unique_market_member')],
            },
        ),
    ]
