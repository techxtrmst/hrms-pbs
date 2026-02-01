# Generated migration to remove EL and CO fields
# Made idempotent - checks if columns exist before removing

from django.db import migrations


def safe_remove_el_co_fields(apps, schema_editor):
    """
    Idempotent migration: remove EL and CO fields if they exist.
    """
    from django.db import connection

    def column_exists(table_name, column_name):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_name = %s AND column_name = %s
                """,
                [table_name, column_name],
            )
            return cursor.fetchone() is not None

    columns_to_remove = [
        "earned_leave_allocated",
        "earned_leave_used",
        "comp_off_allocated",
        "comp_off_used",
    ]

    with connection.cursor() as cursor:
        for column in columns_to_remove:
            if column_exists("employees_leavebalance", column):
                cursor.execute(f"ALTER TABLE employees_leavebalance DROP COLUMN {column}")
                print(f"✅ Removed column {column}")
            else:
                print(f"ℹ️ Column {column} already removed")

    print("✅ EL/CO fields migration complete")


class Migration(migrations.Migration):
    dependencies = [
        ("employees", "0011_fix_locationlog_schema"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(safe_remove_el_co_fields, migrations.RunPython.noop),
            ],
            state_operations=[
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
            ],
        ),
    ]
