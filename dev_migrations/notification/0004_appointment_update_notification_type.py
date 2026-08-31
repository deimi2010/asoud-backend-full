from django.db import migrations, models


APPOINTMENT_CHOICES = [
    ('order_confirmed', 'Order Confirmed'),
    ('payment_success', 'Payment Success'),
    ('new_message', 'New Message'),
    ('market_approved', 'Market Approved'),
    ('product_published', 'Product Published'),
    ('discount_available', 'Discount Available'),
    ('system_maintenance', 'System Maintenance'),
    ('security_alert', 'Security Alert'),
    ('appointment_update', 'Appointment update'),
]


class Migration(migrations.Migration):
    dependencies = [
        ('notification', '0003_deviceinstallation'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='notification_type',
            field=models.CharField(
                choices=APPOINTMENT_CHOICES,
                max_length=50,
                verbose_name='Notification Type',
            ),
        ),
        migrations.AlterField(
            model_name='notificationtemplate',
            name='notification_type',
            field=models.CharField(
                choices=APPOINTMENT_CHOICES,
                max_length=50,
                verbose_name='Notification Type',
            ),
        ),
    ]
