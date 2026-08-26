from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('market', '0002_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='marketslider',
            name='url',
            field=models.URLField(blank=True, max_length=500, null=True, verbose_name='Url'),
        ),
    ]
