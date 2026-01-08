# HRMS Email Configuration Setup Script (PowerShell)
# This script helps set up the mandatory email configuration for deployment

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "HRMS Email Configuration Setup" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Host "❌ .env file not found!" -ForegroundColor Red
    Write-Host "Creating .env from .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "✅ .env file created" -ForegroundColor Green
}

# Prompt for Petabytz HR email password
Write-Host ""
Write-Host "📧 Configuring hrms@petabytz.com email..." -ForegroundColor Cyan
Write-Host ""
$SecurePassword = Read-Host "Enter password for hrms@petabytz.com" -AsSecureString
$BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecurePassword)
$PETABYTZ_PASSWORD = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)

# Check if password is empty
if ([string]::IsNullOrWhiteSpace($PETABYTZ_PASSWORD)) {
    Write-Host "❌ Password cannot be empty!" -ForegroundColor Red
    exit 1
}

# Read .env content
$envContent = Get-Content ".env" -Raw

# Update or add PETABYTZ_HR_EMAIL_PASSWORD to .env
if ($envContent -match "PETABYTZ_HR_EMAIL_PASSWORD") {
    # Update existing entry
    $envContent = $envContent -replace "PETABYTZ_HR_EMAIL_PASSWORD=.*", "PETABYTZ_HR_EMAIL_PASSWORD=$PETABYTZ_PASSWORD"
    Write-Host "✅ Updated PETABYTZ_HR_EMAIL_PASSWORD in .env" -ForegroundColor Green
} else {
    # Add new entry
    $envContent += "`n`n# MANDATORY: Petabytz HR Email Configuration`n"
    $envContent += "PETABYTZ_HR_EMAIL_PASSWORD=$PETABYTZ_PASSWORD`n"
    Write-Host "✅ Added PETABYTZ_HR_EMAIL_PASSWORD to .env" -ForegroundColor Green
}

# Write back to .env
Set-Content ".env" $envContent

Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Email Configuration Summary" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "✅ Email Account: hrms@petabytz.com" -ForegroundColor Green
Write-Host "✅ SMTP Host: smtp.office365.com" -ForegroundColor Green
Write-Host "✅ SMTP Port: 587" -ForegroundColor Green
Write-Host "✅ Use TLS: True" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Email Routing Configuration:" -ForegroundColor Yellow
Write-Host "   • Birthday/Anniversary emails → FROM hrms@petabytz.com"
Write-Host "   • Leave requests → TO hrms@petabytz.com + Manager"
Write-Host "   • Regularization requests → TO hrms@petabytz.com + Manager"
Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Next Steps" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Test email configuration:" -ForegroundColor Yellow
Write-Host "   python manage.py send_birthday_anniversary_emails --test"
Write-Host ""
Write-Host "2. Run migrations (if needed):" -ForegroundColor Yellow
Write-Host "   python manage.py migrate"
Write-Host ""
Write-Host "3. Start the server:" -ForegroundColor Yellow
Write-Host "   python manage.py runserver"
Write-Host ""
Write-Host "4. For production deployment:" -ForegroundColor Yellow
Write-Host "   - Set PETABYTZ_HR_EMAIL_PASSWORD as environment variable"
Write-Host "   - Never commit .env file to Git"
Write-Host "   - Use secure password storage (Azure Key Vault, AWS Secrets Manager, etc.)"
Write-Host ""
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "✅ Email configuration complete!" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Cyan
