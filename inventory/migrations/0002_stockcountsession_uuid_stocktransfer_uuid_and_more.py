import uuid
from django.db import migrations, models


def populate_uuids(apps, schema_editor):
    StockCountSession = apps.get_model('inventory', 'StockCountSession')
    StockTransfer = apps.get_model('inventory', 'StockTransfer')
    Warehouse = apps.get_model('inventory', 'Warehouse')
    for obj in StockCountSession.objects.all():
        obj.uuid = uuid.uuid4()
        obj.save(update_fields=['uuid'])
    for obj in StockTransfer.objects.all():
        obj.uuid = uuid.uuid4()
        obj.save(update_fields=['uuid'])
    for obj in Warehouse.objects.all():
        obj.uuid = uuid.uuid4()
        obj.save(update_fields=['uuid'])


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="stockcountsession",
            name="uuid",
            field=models.UUIDField(null=True, db_index=True),
        ),
        migrations.AddField(
            model_name="stocktransfer",
            name="uuid",
            field=models.UUIDField(null=True, db_index=True),
        ),
        migrations.AddField(
            model_name="warehouse",
            name="uuid",
            field=models.UUIDField(null=True, db_index=True),
        ),
        migrations.RunPython(populate_uuids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="stockcountsession",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True),
        ),
        migrations.AlterField(
            model_name="stocktransfer",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True),
        ),
        migrations.AlterField(
            model_name="warehouse",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True),
        ),
    ]
