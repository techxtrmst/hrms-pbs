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
gh secret set STAGING_SSH_HOST --repo $REPO --body "138.128.242.42"
gh secret set STAGING_SSH_USERNAME --repo $REPO --body "dev"
gh secret set STAGING_SSH_PASSWORD --repo $REPO --body "OXP9vh33LFnChVau"
gh secret set STAGING_SSH_PORT --repo $REPO --body "22"
gh secret set STAGING_DEPLOY_PATH --repo $REPO --body "/var/www/hrms-pbs-staging"
gh secret set STAGING_BACKUP_PATH --repo $REPO --body "/var/www/hrms-pbs-staging-backups"

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
gh secret set STAGING_DEBUG --repo $REPO --body "False"
gh secret set STAGING_SECRET_KEY --repo $REPO --body "-a6@yotquastoq*og+m^e62llncp2`$`$wh5g@is*a9%7qo)6)kfk"
gh secret set STAGING_APP_PORT --repo $REPO --body "8421"
gh secret set STAGING_TIME_ZONE --repo $REPO --body "UTC"

# === Database Configuration ===
Write-Host "🗄️ Setting Database Configuration..." -ForegroundColor Cyan
gh secret set STAGING_DB_ENGINE --repo $REPO --body "django.db.backends.postgresql"
gh secret set STAGING_DB_NAME --repo $REPO --body "postgres"
gh secret set STAGING_DB_USER --repo $REPO --body "postgres"
gh secret set STAGING_DB_PASSWORD --repo $REPO --body "postgres"
gh secret set STAGING_DB_HOST --repo $REPO --body "db"
gh secret set STAGING_DB_PORT --repo $REPO --body "5432"

# === Domain and Security ===
Write-Host "🔒 Setting Domain and Security Configuration..." -ForegroundColor Cyan
gh secret set STAGING_ALLOWED_HOSTS --repo $REPO --body $envVars['ALLOWED_HOSTS']
gh secret set STAGING_CSRF_TRUSTED_ORIGINS --repo $REPO --body "http://138.128.242.42,https://petabytzglobal.com,https://www.petabytzglobal.com"

# === CORS Configuration ===
Write-Host "🌐 Setting CORS Configuration..." -ForegroundColor Cyan
gh secret set STAGING_CORS_ALLOW_ALL_ORIGINS --repo $REPO --body "False"

# === Email Configuration ===
Write-Host "📧 Setting Email Configuration..." -ForegroundColor Cyan
gh secret set STAGING_EMAIL_BACKEND --repo $REPO --body "django.core.mail.backends.smtp.EmailBackend"
gh secret set STAGING_EMAIL_HOST --repo $REPO --body "smtp.gmail.com"
gh secret set STAGING_EMAIL_PORT --repo $REPO --body "587"
gh secret set STAGING_EMAIL_USE_TLS --repo $REPO --body "True"
gh secret set STAGING_EMAIL_USE_SSL --repo $REPO --body "False"
gh secret set STAGING_EMAIL_HOST_USER --repo $REPO --body "hrms@petabytz.com"
gh secret set STAGING_EMAIL_HOST_PASSWORD --repo $REPO --body "Rminds@0007"
gh secret set STAGING_DEFAULT_FROM_EMAIL --repo $REPO --body "HRMS <hrms@petabytz.com>"

# === Static and Media Files ===
Write-Host "📁 Setting Static and Media Files Configuration..." -ForegroundColor Cyan
gh secret set STAGING_STATIC_URL --repo $REPO --body "/static/"
gh secret set STAGING_STATIC_ROOT --repo $REPO --body "/app/staticfiles"
gh secret set STAGING_MEDIA_URL --repo $REPO --body "/media/"
gh secret set STAGING_MEDIA_ROOT --repo $REPO --body "/app/media"

# === PostHog Configuration ===
Write-Host "📊 Setting PostHog Configuration..." -ForegroundColor Cyan
if ($envVars['POSTHOG_API_KEY']) {
    gh secret set STAGING_POSTHOG_API_KEY --repo $REPO --body $envVars['POSTHOG_API_KEY']
    gh secret set STAGING_POSTHOG_HOST --repo $REPO --body $envVars['POSTHOG_HOST']
    gh secret set STAGING_POSTHOG_ENABLED --repo $REPO --body $envVars['POSTHOG_ENABLED']
    Write-Host "✅ PostHog configuration set from .env.staging" -ForegroundColor Green
} else {
    Write-Host "⚠️ POSTHOG_API_KEY not found in .env.staging - skipping" -ForegroundColor Yellow
}

# === Logging Configuration ===
Write-Host "📝 Setting Logging Configuration..." -ForegroundColor Cyan
gh secret set STAGING_LOG_LEVEL --repo $REPO --body "INFO"

Write-Host ""
Write-Host "✅ All secrets have been configured!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Yellow
Write-Host "   1. Create a 'staging' branch if it doesn't exist" -ForegroundColor Gray
Write-Host "   2. Push to the staging branch to trigger deployment" -ForegroundColor Gray
Write-Host "   3. Monitor the GitHub Actions workflow" -ForegroundColor Gray
Write-Host ""
Write-Host "🌐 Application will be available at: http://138.128.242.42:8421" -ForegroundColor Cyan
