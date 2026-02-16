# Generated manually to remove is_activity_tracking_enabled column

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('employees', '0033_employee_pseudo_name'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE employees_employee DROP COLUMN IF EXISTS is_activity_tracking_enabled;",
            reverse_sql="ALTER TABLE employees_employee ADD COLUMN is_activity_tracking_enabled BOOLEAN DEFAULT FALSE NOT NULL;",
        ),
    ]
