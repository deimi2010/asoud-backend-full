import uuid

import django.db.models.deletion
import django.core.validators
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('referral', '0004_store_access'),
        ('payment', '0002_initial'),
        ('market', '0005_market_revision'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ReferralLevel',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, null=True, verbose_name='Updated at')),
                ('level', models.PositiveSmallIntegerField(unique=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(7)])),
                ('percentage', models.DecimalField(decimal_places=2, max_digits=5, validators=[django.core.validators.MinValueValidator(Decimal('0')), django.core.validators.MaxValueValidator(Decimal('100'))])),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={'ordering': ('level',)},
        ),
        migrations.CreateModel(
            name='ReferralCommission',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, null=True, verbose_name='Updated at')),
                ('level', models.PositiveSmallIntegerField()),
                ('base_amount', models.DecimalField(decimal_places=2, max_digits=18)),
                ('percentage', models.DecimalField(decimal_places=2, max_digits=5)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=18)),
                ('status', models.CharField(choices=[('accrued', 'Accrued'), ('paid', 'Paid'), ('canceled', 'Canceled')], default='accrued', max_length=16)),
                ('beneficiary', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='referral_commissions', to=settings.AUTH_USER_MODEL)),
                ('market', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='referral_commissions', to='market.market')),
                ('payment', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='referral_commissions', to='payment.payment')),
                ('source_user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='generated_referral_commissions', to=settings.AUTH_USER_MODEL)),
            ],
            options={'indexes': [models.Index(fields=['beneficiary', 'status'], name='commission_beneficiary_idx')]},
        ),
        migrations.AddConstraint(
            model_name='referralcommission',
            constraint=models.UniqueConstraint(fields=('payment', 'beneficiary', 'level'), name='unique_payment_referral_commission'),
        ),
    ]
