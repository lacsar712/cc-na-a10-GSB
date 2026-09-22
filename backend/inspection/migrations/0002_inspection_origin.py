import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inspection", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="inspection",
            name="origin",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="retests",
                to="inspection.inspection",
                verbose_name="所依原单",
            ),
        ),
    ]
