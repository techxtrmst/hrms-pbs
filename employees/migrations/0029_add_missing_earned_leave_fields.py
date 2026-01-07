# Generated manually to fix missing earned leave fields

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("employees", "0028_add_missing_attendance_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="leavebalance",
            name="earned_leave_allocated",
            field=models.FloatField(
                default=12.0, help_text="Total EL allocated per year"
            ),
        ),
        migrations.AddField(
            model_name="leavebalance",
            name="earned_leave_used",
            field=models.FloatField(default=0.0),
        ),
    ]
