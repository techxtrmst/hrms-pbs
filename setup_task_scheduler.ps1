# PowerShell script to automatically create Windows Task Scheduler task
# Run this script as Administrator

$taskName = "HRMS Birthday Anniversary Emails (Timezone-Aware)"
$taskDescription = "Send birthday and work anniversary emails based on employee location timezone - runs hourly"
$scriptPath = "c:\Users\sathi\Downloads\HRMS_PBS"
$pythonCommand = "python"
$arguments = "manage.py send_birthday_anniversary_emails --hour 9"

# Create the action
$action = New-ScheduledTaskAction -Execute $pythonCommand -Argument $arguments -WorkingDirectory $scriptPath

# Create the trigger (hourly, every day)
$trigger = New-ScheduledTaskTrigger -Once -At "12:00AM" -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Days 9999)

# Create the principal (run with highest privileges)
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType S4U -RunLevel Highest

# Create settings
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 30)

# Register the task
try {
    Register-ScheduledTask `
        -TaskName $taskName `
        -Description $taskDescription `
        -Action $action `
        -Trigger $trigger `
        -Principal $principal `
        -Settings $settings `
        -Force

    Write-Host "✅ Task Scheduler task created successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Task Name: $taskName" -ForegroundColor Cyan
    Write-Host "Schedule: Every hour, 24/7" -ForegroundColor Cyan
    Write-Host "Target Time: 9:00 AM in employee's local timezone" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "To test the task immediately:" -ForegroundColor Yellow
    Write-Host "1. Open Task Scheduler (Win + R, type 'taskschd.msc')" -ForegroundColor Yellow
    Write-Host "2. Find '$taskName' in the task list" -ForegroundColor Yellow
    Write-Host "3. Right-click and select 'Run'" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Or run this command:" -ForegroundColor Yellow
    Write-Host "Start-ScheduledTask -TaskName '$taskName'" -ForegroundColor White
}
catch {
    Write-Host "❌ Error creating task: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please run this script as Administrator" -ForegroundColor Yellow
}
