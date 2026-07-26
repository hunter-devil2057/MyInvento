from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='khalti_pidx',
            field=models.CharField(blank=True, max_length=64, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='payment',
            name='khalti_transaction_id',
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AlterField(
            model_name='payment',
            name='method',
            field=models.CharField(choices=[
                ('Cash', 'Cash'),
                ('Card', 'Card'),
                ('Mobile Wallet', 'Mobile Wallet'),
                ('Bank Transfer', 'Bank Transfer'),
                ('Store Credit', 'Store Credit'),
                ('Khalti', 'Khalti'),
            ], max_length=20),
        ),
        migrations.AlterField(
            model_name='payment',
            name='status',
            field=models.CharField(choices=[
                ('Paid', 'Paid'),
                ('Partially Paid', 'Partially Paid'),
                ('Refunded', 'Refunded'),
                ('Pending', 'Pending'),
            ], default='Paid', max_length=20),
        ),
    ]
