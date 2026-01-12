#!/usr/bin/env python3
"""
Post-Merge Testing Script
Verifies all HRMS functionality after Git merge and migration sync
"""

import os
import sys
import subprocess
from datetime import datetime

def run_command(command, description):
    """Run a command and return success status"""
    print(f"\n🔍 {description}")
    print(f"Command: {command}")
    print("-" * 50)
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ SUCCESS")
            if result.stdout.strip():
                print("Output:", result.stdout.strip()[:500])  # Limit output
            return True
        else:
            print("❌ FAILED")
            print("Error:", result.stderr.strip())
            return False
            
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        return False

def test_django_system():
    """Test basic Django system functionality"""
    print("\n" + "="*60)
    print("🔧 TESTING DJANGO SYSTEM")
    print("="*60)
    
    tests = [
        ("python manage.py check", "Django System Check"),
        ("python manage.py showmigrations", "Migration Status"),
        ("python manage.py migrate --dry-run", "Migration Dry Run"),
    ]
    
    results = []
    for command, description in tests:
        success = run_command(command, description)
        results.append((description, success))
    
    return results

def test_attendance_system():
    """Test attendance and clock-in/out functionality"""
    print("\n" + "="*60)
    print("⏰ TESTING ATTENDANCE SYSTEM")
    print("="*60)
    
    tests = [
        ("python manage.py auto_clockout_previous_day --dry-run", "Auto Clock-Out System"),
        ("python manage.py fix_attendance_hours --days 7 --dry-run", "Attendance Hours Fix"),
        ("python manage.py test_session_combination --dry-run", "Session Combination Test"),
    ]
    
    results = []
    for command, description in tests:
        success = run_command(command, description)
        results.append((description, success))
    
    return results

def test_leave_system():
    """Test leave allocation and management"""
    print("\n" + "="*60)
    print("🏖️ TESTING LEAVE SYSTEM")
    print("="*60)
    
    tests = [
        ("python manage.py accrue_monthly_leaves_by_company --dry-run", "Monthly Leave Accrual"),
        ("python manage.py add_previous_leaves --employee-id 1 --casual-leave 1.0 --dry-run", "Previous Leave Addition"),
    ]
    
    results = []
    for command, description in tests:
        success = run_command(command, description)
        results.append((description, success))
    
    return results

def test_holiday_system():
    """Test holiday and week-off management"""
    print("\n" + "="*60)
    print("🎉 TESTING HOLIDAY SYSTEM")
    print("="*60)
    
    tests = [
        ("python manage.py mark_holidays --dry-run", "Holiday Management"),
    ]
    
    results = []
    for command, description in tests:
        success = run_command(command, description)
        results.append((description, success))
    
    return results

def check_file_integrity():
    """Check if our key files are still intact"""
    print("\n" + "="*60)
    print("📁 CHECKING FILE INTEGRITY")
    print("="*60)
    
    key_files = [
        "employees/management/commands/auto_clockout_previous_day.py",
        "employees/management/commands/fix_attendance_hours.py",
        "employees/management/commands/test_session_combination.py",
        "employees/management/commands/add_previous_leaves.py",
        "employees/management/commands/accrue_monthly_leaves_by_company.py",
        "employees/management/commands/setup_monthly_leave_allocation.py",
        "core/templates/core/personal_home.html",
        "employees/models.py",
        "employees/views.py",
        "core/views.py",
    ]
    
    results = []
    for file_path in key_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
            results.append((file_path, True))
        else:
            print(f"❌ {file_path} - MISSING!")
            results.append((file_path, False))
    
    return results

def generate_report(all_results):
    """Generate a comprehensive test report"""
    print("\n" + "="*60)
    print("📊 POST-MERGE TEST REPORT")
    print("="*60)
    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    total_tests = 0
    passed_tests = 0
    
    for category, results in all_results.items():
        print(f"\n📋 {category}:")
        for test_name, success in results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"   {status} - {test_name}")
            total_tests += 1
            if success:
                passed_tests += 1
    
    print(f"\n🎯 SUMMARY:")
    print(f"   Total Tests: {total_tests}")
    print(f"   Passed: {passed_tests}")
    print(f"   Failed: {total_tests - passed_tests}")
    print(f"   Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED! System is ready for use.")
        return True
    else:
        print(f"\n⚠️  {total_tests - passed_tests} TESTS FAILED! Review and fix issues.")
        return False

def main():
    """Main testing function"""
    print("🚀 HRMS POST-MERGE TESTING")
    print("=" * 60)
    print("This script will test all HRMS functionality after Git merge")
    print("Ensure you have:")
    print("1. ✅ Merged the PR")
    print("2. ✅ Pulled latest changes (git pull origin main)")
    print("3. ✅ Run migrations (python manage.py migrate)")
    
    input("\nPress Enter to start testing...")
    
    # Run all test categories
    all_results = {}
    
    # Test Django system
    all_results["Django System"] = test_django_system()
    
    # Test attendance system
    all_results["Attendance System"] = test_attendance_system()
    
    # Test leave system
    all_results["Leave System"] = test_leave_system()
    
    # Test holiday system
    all_results["Holiday System"] = test_holiday_system()
    
    # Check file integrity
    all_results["File Integrity"] = check_file_integrity()
    
    # Generate final report
    success = generate_report(all_results)
    
    if success:
        print("\n🎊 CONGRATULATIONS!")
        print("All systems are working correctly after the merge.")
        print("\n📋 Next Steps:")
        print("1. ✅ Test the web interface manually")
        print("2. ✅ Verify clock-in/clock-out functionality")
        print("3. ✅ Check attendance reports")
        print("4. ✅ Test leave management")
        print("5. ✅ Setup daily auto clock-out cron job")
    else:
        print("\n🔧 ACTION REQUIRED:")
        print("Some tests failed. Please review the errors above and:")
        print("1. Check for migration conflicts")
        print("2. Verify file integrity")
        print("3. Re-run failed commands manually")
        print("4. Contact support if issues persist")
    
    return success

if __name__ == "__main__":
    main()