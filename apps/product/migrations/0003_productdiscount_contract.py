import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0002_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productdiscount',
            name='percentage',
            field=models.PositiveSmallIntegerField(
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(99),
                ],
                verbose_name='Percentage',
            ),
        ),
        migrations.AlterField(
            model_name='productdiscount',
            name='product',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='automatic_discounts',
                to='product.product',
                verbose_name='Product',
            ),
        ),
        migrations.AddField(
            model_name='productdiscount',
            name='discount_type',
            field=models.CharField(
                choices=[('percent', 'Percentage'), ('timed', 'Timed'), ('group', 'Group')],
                default='percent',
                max_length=12,
            ),
        ),
        migrations.AddField(
            model_name='productdiscount',
            name='expiry',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='productdiscount',
            name='limitation',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='productdiscount',
            name='consumed',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='productdiscount',
            name='reserved',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='productdiscount',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
    ]
