from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('market', '0006_market_business_id_length'),
    ]

    operations = [
        migrations.AddField(
            model_name='market',
            name='status_reason',
            field=models.TextField(blank=True, default='', verbose_name='Status reason'),
        ),
    ]
