from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('market', '0005_market_revision'),
    ]

    operations = [
        migrations.AlterField(
            model_name='market',
            name='business_id',
            field=models.CharField(max_length=63, unique=True, verbose_name='Business id'),
        ),
    ]
