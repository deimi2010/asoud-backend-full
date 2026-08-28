import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('chat', '0002_initial'),
        ('market', '0004_marketshippingmethod'),
        ('product', '0006_product_theme_integrity'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='chatroom',
            name='object_id',
            field=models.CharField(
                blank=True,
                max_length=64,
                null=True,
                verbose_name='Object ID',
            ),
        ),
        migrations.AddField(
            model_name='chatroom',
            name='customer',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='market_chat_rooms',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Customer',
            ),
        ),
        migrations.AddField(
            model_name='chatroom',
            name='market',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='chat_rooms',
                to='market.market',
                verbose_name='Market',
            ),
        ),
        migrations.AddField(
            model_name='chatmessage',
            name='client_id',
            field=models.UUIDField(
                blank=True,
                null=True,
                verbose_name='Client Message ID',
            ),
        ),
        migrations.AddField(
            model_name='chatmessage',
            name='product',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='chat_messages',
                to='product.product',
                verbose_name='Related Product',
            ),
        ),
        migrations.AlterField(
            model_name='chatmessage',
            name='message_type',
            field=models.CharField(
                choices=[
                    ('text', 'Text'),
                    ('image', 'Image'),
                    ('file', 'File'),
                    ('audio', 'Audio'),
                    ('video', 'Video'),
                    ('location', 'Location'),
                    ('system', 'System'),
                    ('product', 'Product'),
                ],
                default='text',
                max_length=20,
                verbose_name='Message Type',
            ),
        ),
        migrations.AddIndex(
            model_name='chatroom',
            index=models.Index(
                fields=['market', 'customer'],
                name='chat_conver_market__60013f_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='chatmessage',
            index=models.Index(fields=['product'], name='chat_messag_product_6e1828_idx'),
        ),
        migrations.AddConstraint(
            model_name='chatmessage',
            constraint=models.UniqueConstraint(
                condition=models.Q(client_id__isnull=False),
                fields=('sender', 'client_id'),
                name='uniq_chat_sender_client_message',
            ),
        ),
        migrations.AddConstraint(
            model_name='chatroom',
            constraint=models.UniqueConstraint(
                condition=models.Q(room_type='market'),
                fields=('market', 'customer'),
                name='uniq_market_customer_chat',
            ),
        ),
    ]
