from django.db import migrations, models


def fix_locationlog_schema(apps, schema_editor):
    from django.db import connection, transaction

    # We use a raw cursor to handle this safely across different potential states
    with connection.cursor() as cursor:
        # Check if column exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='employees_locationlog' AND column_name='attendance_session_id'
        """)
        if not cursor.fetchone():
            print(
                "Adding missing column 'attendance_session_id' to 'employees_locationlog'"
            )
            # Add column - using bigint because DEFAULT_AUTO_FIELD is BigAutoField
            cursor.execute("""
                ALTER TABLE employees_locationlog 
                ADD COLUMN attendance_session_id bigint NULL
            """)

            # Add FK constraint
            print("Adding foreign key constraint")
            cursor.execute("""
                ALTER TABLE employees_locationlog
                ADD CONSTRAINT employees_locationlog_attendance_session_id_fk_employees_attendancesession_id
                FOREIGN KEY (attendance_session_id) 
                REFERENCES employees_attendancesession(id)
                DEFERRABLE INITIALLY DEFERRED
            """)

            # Create index
            print("Creating index")
            cursor.execute("""
                CREATE INDEX employees_locationlog_attendance_session_id_idx 
                ON employees_locationlog(attendance_session_id)
            """)
        else:
            print(
                "Column 'attendance_session_id' already exists in 'employees_locationlog'"
            )


class Migration(migrations.Migration):
    dependencies = [
        ("employees", "0010_reset_migration_state_for_staging"),
    ]

    operations = [
        migrations.RunPython(fix_locationlog_schema, migrations.RunPython.noop),
    ]
