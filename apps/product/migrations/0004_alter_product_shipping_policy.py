from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product', '0003_productdiscount_contract'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='ship_cost_pay_type',
            field=models.CharField(
                choices=[
                    ('market', 'Market'),
                    ('customer', 'Customer'),
                    ('free', 'Free'),
                    ('none', 'No shipping'),
                    ('store', 'Use store shipping methods'),
                ],
                max_length=10,
                verbose_name='Ship cost pay type',
            ),
        ),
    ]
