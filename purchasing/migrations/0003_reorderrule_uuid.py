import uuid
from django.db import migrations, models


def populate_reorder_uuids(apps, schema_editor):
    ReorderRule = apps.get_model('purchasing', 'ReorderRule')
    for obj in ReorderRule.objects.all():
        obj.uuid = uuid.uuid4()
        obj.save(update_fields=['uuid'])


class Migration(migrations.Migration):

    dependencies = [
        ("purchasing", "0002_purchaseorder_uuid"),
    ]

    operations = [
        migrations.AddField(
            model_name="reorderrule",
            name="uuid",
            field=models.UUIDField(null=True, db_index=True),
        ),
        migrations.RunPython(populate_reorder_uuids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="reorderrule",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True),
        ),
    ]
