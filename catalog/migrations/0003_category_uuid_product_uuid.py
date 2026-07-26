import uuid
from django.db import migrations, models


def populate_uuids(apps, schema_editor):
    Category = apps.get_model('catalog', 'Category')
    Product = apps.get_model('catalog', 'Product')
    for obj in Category.objects.all():
        obj.uuid = uuid.uuid4()
        obj.save(update_fields=['uuid'])
    for obj in Product.objects.all():
        obj.uuid = uuid.uuid4()
        obj.save(update_fields=['uuid'])


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0002_product_image_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="uuid",
            field=models.UUIDField(null=True, db_index=True),
        ),
        migrations.AddField(
            model_name="product",
            name="uuid",
            field=models.UUIDField(null=True, db_index=True),
        ),
        migrations.RunPython(populate_uuids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="category",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True),
        ),
        migrations.AlterField(
            model_name="product",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True),
        ),
    ]
