# Generated manually to fix missing attendance fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('employees', '0002_add_session_tracking_fields'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            -- Add missing columns to employees_attendance table
            ALTER TABLE employees_attendance 
            ADD COLUMN IF NOT EXISTS daily_sessions_count INTEGER DEFAULT 0;
            
            ALTER TABLE employees_attendance 
            ADD COLUMN IF NOT EXISTS max_daily_sessions INTEGER DEFAULT 3;
            
            ALTER TABLE employees_attendance 
            ADD COLUMN IF NOT EXISTS current_session_type VARCHAR(20);
            
            ALTER TABLE employees_attendance 
            ADD COLUMN IF NOT EXISTS user_timezone VARCHAR(50) DEFAULT 'Asia/Kolkata';
            """,
            reverse_sql="""
            ALTER TABLE employees_attendance DROP COLUMN IF EXISTS daily_sessions_count;
            ALTER TABLE employees_attendance DROP COLUMN IF EXISTS max_daily_sessions;
            ALTER TABLE employees_attendance DROP COLUMN IF EXISTS current_session_type;
            ALTER TABLE employees_attendance DROP COLUMN IF EXISTS user_timezone;
            """,
        ),
    ]
