import uuid
from django.db import migrations, models


def populate_channel_uuids(apps, schema_editor):
    SalesChannel = apps.get_model('sales', 'SalesChannel')
    for obj in SalesChannel.objects.all():
        obj.uuid = uuid.uuid4()
        obj.save(update_fields=['uuid'])


class Migration(migrations.Migration):

    dependencies = [
        ("sales", "0003_customer_uuid_return_uuid_salestransaction_uuid"),
    ]

    operations = [
        migrations.AddField(
            model_name="saleschannel",
            name="uuid",
            field=models.UUIDField(null=True, db_index=True),
        ),
        migrations.RunPython(populate_channel_uuids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="saleschannel",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True),
        ),
    ]
