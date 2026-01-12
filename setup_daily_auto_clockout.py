#!/usr/bin/env python3
"""
Setup script for daily auto clock-out cron job
This script should be run once to set up automatic daily clock-out for incomplete sessions
"""

import os
import subprocess
import sys
from pathlib import Path

def setup_cron_job():
    """Setup cron job for daily auto clock-out"""
    
    # Get current directory (where manage.py is located)
    current_dir = Path(__file__).parent.absolute()
    manage_py_path = current_dir / "manage.py"
    
    if not manage_py_path.exists():
        print("❌ Error: manage.py not found in current directory")
        return False
    
    # Cron job command
    cron_command = f"0 6 * * * cd {current_dir} && python manage.py auto_clockout_previous_day"
    
    print("🔧 Setting up daily auto clock-out cron job...")
    print(f"📁 Project directory: {current_dir}")
    print(f"⏰ Schedule: Daily at 6:00 AM")
    print(f"🔄 Command: {cron_command}")
    
    try:
        # Get current crontab
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        current_crontab = result.stdout if result.returncode == 0 else ""
        
        # Check if job already exists
        if "auto_clockout_previous_day" in current_crontab:
            print("⚠️  Auto clock-out cron job already exists")
            print("Current crontab:")
            print(current_crontab)
            return True
        
        # Add new cron job
        new_crontab = current_crontab + f"\n{cron_command}\n"
        
        # Write new crontab
        process = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, text=True)
        process.communicate(input=new_crontab)
        
        if process.returncode == 0:
            print("✅ Cron job added successfully!")
            print("\n📋 Current crontab:")
            subprocess.run(['crontab', '-l'])
            return True
        else:
            print("❌ Failed to add cron job")
            return False
            
    except FileNotFoundError:
        print("❌ Error: crontab command not found")
        print("💡 Manual setup required:")
        print(f"   Add this line to your crontab (run 'crontab -e'):")
        print(f"   {cron_command}")
        return False
    except Exception as e:
        print(f"❌ Error setting up cron job: {e}")
        return False

def setup_windows_task():
    """Setup Windows Task Scheduler for daily auto clock-out"""
    
    current_dir = Path(__file__).parent.absolute()
    python_exe = sys.executable
    manage_py_path = current_dir / "manage.py"
    
    task_name = "HRMS_Auto_ClockOut"
    task_command = f'"{python_exe}" "{manage_py_path}" auto_clockout_previous_day'
    
    print("🔧 Setting up Windows Task Scheduler job...")
    print(f"📁 Project directory: {current_dir}")
    print(f"🐍 Python executable: {python_exe}")
    print(f"⏰ Schedule: Daily at 6:00 AM")
    
    # Create PowerShell script to set up task
    ps_script = f'''
$TaskName = "{task_name}"
$TaskPath = "\\HRMS\\"
$Action = New-ScheduledTaskAction -Execute '"{python_exe}"' -Argument '"{manage_py_path}" auto_clockout_previous_day' -WorkingDirectory "{current_dir}"
$Trigger = New-ScheduledTaskTrigger -Daily -At "06:00"
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive

# Check if task exists
$ExistingTask = Get-ScheduledTask -TaskName $TaskName -TaskPath $TaskPath -ErrorAction SilentlyContinue

if ($ExistingTask) {{
    Write-Host "⚠️  Task already exists: $TaskName"
    Write-Host "Current task details:"
    Get-ScheduledTask -TaskName $TaskName -TaskPath $TaskPath | Format-List
}} else {{
    # Create the task
    Register-ScheduledTask -TaskName $TaskName -TaskPath $TaskPath -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Description "HRMS Auto Clock-Out for incomplete sessions"
    Write-Host "✅ Windows Task created successfully!"
    Write-Host "Task Name: $TaskName"
    Write-Host "Task Path: $TaskPath"
}}
'''
    
    try:
        # Run PowerShell script
        result = subprocess.run(
            ['powershell', '-Command', ps_script],
            capture_output=True,
            text=True,
            shell=True
        )
        
        if result.returncode == 0:
            print("✅ Windows Task Scheduler setup completed!")
            print(result.stdout)
            return True
        else:
            print("❌ Failed to create Windows Task")
            print("Error:", result.stderr)
            print("\n💡 Manual setup instructions:")
            print("1. Open Task Scheduler (taskschd.msc)")
            print("2. Create Basic Task")
            print(f"3. Name: {task_name}")
            print("4. Trigger: Daily at 6:00 AM")
            print(f"5. Action: Start a program")
            print(f"6. Program: {python_exe}")
            print(f"7. Arguments: {manage_py_path} auto_clockout_previous_day")
            print(f"8. Start in: {current_dir}")
            return False
            
    except Exception as e:
        print(f"❌ Error setting up Windows Task: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 HRMS Auto Clock-Out Setup")
    print("=" * 50)
    
    # Detect operating system
    if os.name == 'nt':  # Windows
        print("🖥️  Detected: Windows")
        success = setup_windows_task()
    else:  # Unix-like (Linux, macOS)
        print("🐧 Detected: Unix-like system")
        success = setup_cron_job()
    
    if success:
        print("\n🎉 Setup completed successfully!")
        print("\n📋 What happens now:")
        print("   • Every day at 6:00 AM, the system will:")
        print("   • Check for employees who forgot to clock out yesterday")
        print("   • Automatically clock them out at 23:59")
        print("   • Calculate their working hours properly")
        print("   • Allow them to clock in fresh today")
        
        print("\n🔧 Manual commands:")
        print("   # Run auto clock-out manually")
        print("   python manage.py auto_clockout_previous_day")
        print("   ")
        print("   # Check what would be fixed (dry run)")
        print("   python manage.py auto_clockout_previous_day --dry-run")
        print("   ")
        print("   # Fix last 3 days")
        print("   python manage.py auto_clockout_previous_day --days-back 3")
        
    else:
        print("\n❌ Setup failed - manual configuration required")
        print("Please refer to the manual setup instructions above")
    
    return success

if __name__ == "__main__":
    main()