import uuid
from django.db import migrations, models


def populate_uuids(apps, schema_editor):
    Customer = apps.get_model('sales', 'Customer')
    Return = apps.get_model('sales', 'Return')
    SalesTransaction = apps.get_model('sales', 'SalesTransaction')
    for obj in Customer.objects.all():
        obj.uuid = uuid.uuid4()
        obj.save(update_fields=['uuid'])
    for obj in Return.objects.all():
        obj.uuid = uuid.uuid4()
        obj.save(update_fields=['uuid'])
    for obj in SalesTransaction.objects.all():
        obj.uuid = uuid.uuid4()
        obj.save(update_fields=['uuid'])


class Migration(migrations.Migration):

    dependencies = [
        ("sales", "0002_payment_khalti_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="customer",
            name="uuid",
            field=models.UUIDField(null=True, db_index=True),
        ),
        migrations.AddField(
            model_name="return",
            name="uuid",
            field=models.UUIDField(null=True, db_index=True),
        ),
        migrations.AddField(
            model_name="salestransaction",
            name="uuid",
            field=models.UUIDField(null=True, db_index=True),
        ),
        migrations.RunPython(populate_uuids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="customer",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True),
        ),
        migrations.AlterField(
            model_name="return",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True),
        ),
        migrations.AlterField(
            model_name="salestransaction",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True),
        ),
    ]
