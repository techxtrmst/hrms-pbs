#!/usr/bin/env python
import sqlite3
import os

# Check if database exists
if os.path.exists('db.sqlite3'):
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    
    # Check if employees_leavebalance table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='employees_leavebalance'")
    table_exists = cursor.fetchone()
    
    if table_exists:
        print("✅ employees_leavebalance table exists")
        
        # Get table schema
        cursor.execute("PRAGMA table_info(employees_leavebalance)")
        columns = cursor.fetchall()
        
        print("\n📋 Current table columns:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        
        # Check for specific missing column
        column_names = [col[1] for col in columns]
        required_columns = [
            'earned_leave_allocated',
            'casual_leave_allocated', 
            'sick_leave_allocated',
            'comp_off_allocated'
        ]
        
        print("\n🔍 Checking required columns:")
        for req_col in required_columns:
            if req_col in column_names:
                print(f"  ✅ {req_col}")
            else:
                print(f"  ❌ {req_col} - MISSING")
    else:
        print("❌ employees_leavebalance table does not exist")
    
    conn.close()
else:
    print("❌ Database file db.sqlite3 not found")