# Generated migration to remove EL and CO fields

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("employees", "0011_fix_locationlog_schema"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="leavebalance",
            name="earned_leave_allocated",
        ),
        migrations.RemoveField(
            model_name="leavebalance",
            name="earned_leave_used",
        ),
        migrations.RemoveField(
            model_name="leavebalance",
            name="comp_off_allocated",
        ),
        migrations.RemoveField(
            model_name="leavebalance",
            name="comp_off_used",
        ),
    ]
