#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

from django.db import connection

def check_postgres_schema():
    print("🔍 CHECKING POSTGRESQL SCHEMA")
    print("=" * 50)
    
    with connection.cursor() as cursor:
        # Check if employees_leavebalance table exists
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'employees_leavebalance'
        """)
        
        table_exists = cursor.fetchone()
        
        if table_exists:
            print("✅ employees_leavebalance table exists")
            
            # Get column information
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'employees_leavebalance'
                ORDER BY ordinal_position
            """)
            
            columns = cursor.fetchall()
            
            print("\n📋 Current table columns:")
            for col in columns:
                print(f"  - {col[0]} ({col[1]}) {'NULL' if col[2] == 'YES' else 'NOT NULL'}")
            
            # Check for specific missing columns
            column_names = [col[0] for col in columns]
            required_columns = [
                'earned_leave_allocated',
                'casual_leave_allocated', 
                'sick_leave_allocated',
                'comp_off_allocated',
                'earned_leave_used',
                'casual_leave_used',
                'sick_leave_used',
                'comp_off_used'
            ]
            
            print("\n🔍 Checking required columns:")
            missing_columns = []
            for req_col in required_columns:
                if req_col in column_names:
                    print(f"  ✅ {req_col}")
                else:
                    print(f"  ❌ {req_col} - MISSING")
                    missing_columns.append(req_col)
            
            if missing_columns:
                print(f"\n⚠️  Missing columns: {missing_columns}")
                print("\n🔧 SOLUTION:")
                print("The migration was marked as applied but the columns are missing.")
                print("This can happen if the migration failed partway through.")
                print("\nOptions to fix:")
                print("1. Manually add the missing columns")
                print("2. Reset the migration and re-run it")
                print("3. Create a new migration to add missing columns")
            else:
                print("\n✅ All required columns are present!")
                
        else:
            print("❌ employees_leavebalance table does not exist")
            print("This suggests the LeaveBalance model migration never ran.")

if __name__ == '__main__':
    check_postgres_schema()