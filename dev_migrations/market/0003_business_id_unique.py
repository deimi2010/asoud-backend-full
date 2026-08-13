from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('market', '0002_initial')]

    operations = [
        migrations.AlterField(
            model_name='market',
            name='business_id',
            field=models.CharField(max_length=20, unique=True, verbose_name='Business id'),
        ),
    ]
