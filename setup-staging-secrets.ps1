# HRMS PBS Staging Secrets Setup Script
# This script helps set up GitHub Actions secrets for staging deployment
# Run this script from PowerShell with GitHub CLI installed and authenticated

# Repository name (update this to match your repository)
$REPO = "techxtrmst/hrms-pbs"

Write-Host "🔐 Setting up GitHub Actions secrets for HRMS PBS Staging Deployment" -ForegroundColor Cyan
Write-Host "Repository: $REPO" -ForegroundColor Yellow
Write-Host ""

# Check if GitHub CLI is installed
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "❌ GitHub CLI (gh) is not installed. Please install it first:" -ForegroundColor Red
    Write-Host "   winget install GitHub.cli" -ForegroundColor Gray
    exit 1
}

# Check if authenticated
$authStatus = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Please authenticate with GitHub CLI first:" -ForegroundColor Red
    Write-Host "   gh auth login" -ForegroundColor Gray
    exit 1
}

Write-Host "✅ GitHub CLI authenticated" -ForegroundColor Green
Write-Host ""

# Load environment variables from .env.staging
$envFile = Join-Path $PSScriptRoot ".env.staging"
if (-not (Test-Path $envFile)) {
    Write-Host "❌ .env.staging file not found at: $envFile" -ForegroundColor Red
    exit 1
}

# Parse .env.staging file
$envVars = @{}
Get-Content $envFile | Where-Object { $_ -match '^\s*[^#]' } | ForEach-Object {
    $line = $_.Trim()
    if ($line -match '^([^=]+)=(.*)$') {
        $key = $matches[1]
        $value = $matches[2]
        $envVars[$key] = $value
    }
}

# === SSH Configuration ===
Write-Host "📡 Setting SSH Configuration..." -ForegroundColor Cyan
gh secret set STAGING_SSH_HOST --repo $REPO --body $envVars['STAGING_SSH_HOST']
gh secret set STAGING_SSH_USERNAME --repo $REPO --body $envVars['STAGING_SSH_USERNAME']
gh secret set STAGING_SSH_PASSWORD --repo $REPO --body $envVars['STAGING_SSH_PASSWORD']
gh secret set STAGING_SSH_PORT --repo $REPO --body $envVars['STAGING_SSH_PORT']
gh secret set STAGING_DEPLOY_PATH --repo $REPO --body $envVars['STAGING_DEPLOY_PATH']
gh secret set STAGING_BACKUP_PATH --repo $REPO --body $envVars['STAGING_BACKUP_PATH']

# === MS Teams Notifications ===
Write-Host "📢 Setting Notifications..." -ForegroundColor Cyan
if ($envVars['STAGING_TEAMS_WEBHOOK_URL']) {
    gh secret set STAGING_TEAMS_WEBHOOK_URL --repo $REPO --body $envVars['STAGING_TEAMS_WEBHOOK_URL']
    Write-Host "✅ MS Teams webhook configured" -ForegroundColor Green
} else {
    Write-Host "⚠️ STAGING_TEAMS_WEBHOOK_URL not found in .env.staging - skipping" -ForegroundColor Yellow
}

# === Django Configuration ===
Write-Host "🐍 Setting Django Configuration..." -ForegroundColor Cyan
gh secret set STAGING_DEBUG --repo $REPO --body $envVars['DEBUG']
gh secret set STAGING_SECRET_KEY --repo $REPO --body $envVars['SECRET_KEY']
gh secret set STAGING_APP_PORT --repo $REPO --body $envVars['APP_PORT']
gh secret set STAGING_TIME_ZONE --repo $REPO --body $envVars['TIME_ZONE']

# === Database Configuration ===
Write-Host "🗄️ Setting Database Configuration..." -ForegroundColor Cyan
gh secret set STAGING_DB_ENGINE --repo $REPO --body $envVars['DB_ENGINE']
gh secret set STAGING_DB_NAME --repo $REPO --body $envVars['DB_NAME']
gh secret set STAGING_DB_USER --repo $REPO --body $envVars['DB_USER']
gh secret set STAGING_DB_PASSWORD --repo $REPO --body $envVars['DB_PASSWORD']
gh secret set STAGING_DB_HOST --repo $REPO --body $envVars['DB_HOST']
gh secret set STAGING_DB_PORT --repo $REPO --body $envVars['DB_PORT']

# === Domain and Security ===
Write-Host "🔒 Setting Domain and Security Configuration..." -ForegroundColor Cyan
gh secret set STAGING_ALLOWED_HOSTS --repo $REPO --body $envVars['ALLOWED_HOSTS']
gh secret set STAGING_CSRF_TRUSTED_ORIGINS --repo $REPO --body $envVars['CSRF_TRUSTED_ORIGINS']

# === CORS Configuration ===
Write-Host "🌐 Setting CORS Configuration..." -ForegroundColor Cyan
gh secret set STAGING_CORS_ALLOW_ALL_ORIGINS --repo $REPO --body $envVars['CORS_ALLOW_ALL_ORIGINS']

# === Email Configuration ===
Write-Host "📧 Setting Email Configuration..." -ForegroundColor Cyan
gh secret set STAGING_EMAIL_BACKEND --repo $REPO --body $envVars['EMAIL_BACKEND']
gh secret set STAGING_EMAIL_HOST --repo $REPO --body $envVars['EMAIL_HOST']
gh secret set STAGING_EMAIL_PORT --repo $REPO --body $envVars['EMAIL_PORT']
gh secret set STAGING_EMAIL_USE_TLS --repo $REPO --body $envVars['EMAIL_USE_TLS']
gh secret set STAGING_EMAIL_USE_SSL --repo $REPO --body $envVars['EMAIL_USE_SSL']
gh secret set STAGING_EMAIL_HOST_USER --repo $REPO --body $envVars['EMAIL_HOST_USER']
gh secret set STAGING_EMAIL_HOST_PASSWORD --repo $REPO --body $envVars['EMAIL_HOST_PASSWORD']
gh secret set STAGING_DEFAULT_FROM_EMAIL --repo $REPO --body $envVars['DEFAULT_FROM_EMAIL']

# === Static and Media Files ===
Write-Host "📁 Setting Static and Media Files Configuration..." -ForegroundColor Cyan
gh secret set STAGING_STATIC_URL --repo $REPO --body $envVars['STATIC_URL']
gh secret set STAGING_STATIC_ROOT --repo $REPO --body $envVars['STATIC_ROOT']
gh secret set STAGING_MEDIA_URL --repo $REPO --body $envVars['MEDIA_URL']
gh secret set STAGING_MEDIA_ROOT --repo $REPO --body $envVars['MEDIA_ROOT']

Write-Host ""
Write-Host "✅ All secrets have been configured!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Yellow
Write-Host "   1. Create a 'staging' branch if it doesn't exist" -ForegroundColor Gray
Write-Host "   2. Push to the staging branch to trigger deployment" -ForegroundColor Gray
Write-Host "   3. Monitor the GitHub Actions workflow" -ForegroundColor Gray
Write-Host ""
Write-Host "🌐 Application will be available at: http://138.128.242.42:8421" -ForegroundColor Cyan
