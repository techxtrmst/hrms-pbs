import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hrms_core.settings")
django.setup()

from django.db import connection
cursor = connection.cursor()
cursor.execute("SELECT column_name, is_nullable, column_default FROM information_schema.columns WHERE table_name = 'employees_attendance'")
print("--- SCHEMA START ---")
for row in cursor.fetchall():
    print(row)
print("--- SCHEMA END ---")
