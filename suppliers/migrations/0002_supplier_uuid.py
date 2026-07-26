import uuid
from django.db import migrations, models


def populate_uuids(apps, schema_editor):
    Supplier = apps.get_model('suppliers', 'Supplier')
    for obj in Supplier.objects.all():
        obj.uuid = uuid.uuid4()
        obj.save(update_fields=['uuid'])


class Migration(migrations.Migration):

    dependencies = [
        ("suppliers", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="supplier",
            name="uuid",
            field=models.UUIDField(null=True, db_index=True),
        ),
        migrations.RunPython(populate_uuids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="supplier",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True),
        ),
    ]
