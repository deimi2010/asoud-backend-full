from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):
    dependencies = [('referral', '0003_market_invites')]

    operations = [
        migrations.CreateModel(
            name='StoreAccess',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, null=True, verbose_name='Updated at')),
                ('verified_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('is_active', models.BooleanField(default=True)),
                ('invite_link', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='store_accesses', to='referral.marketinvitelink')),
                ('market', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='customer_accesses', to='market.market')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='store_accesses', to='users.user')),
            ],
        ),
        migrations.AddConstraint(
            model_name='storeaccess',
            constraint=models.UniqueConstraint(fields=('user', 'market'), name='unique_user_store_access'),
        ),
        migrations.AddIndex(
            model_name='storeaccess',
            index=models.Index(fields=['user', 'is_active'], name='store_access_user_active_idx'),
        ),
        migrations.CreateModel(
            name='SignupInviteIntent',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Created at')),
                ('updated_at', models.DateTimeField(auto_now=True, null=True, verbose_name='Updated at')),
                ('consumed_at', models.DateTimeField(blank=True, null=True)),
                ('invite_link', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='signup_intents', to='referral.marketinvitelink')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='signup_invite_intent', to='users.user')),
            ],
        ),
    ]
