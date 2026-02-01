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
if ($envVars['STAGING_SSH_HOST']) {
    gh secret set STAGING_SSH_HOST --repo $REPO --body $envVars['STAGING_SSH_HOST']
    gh secret set STAGING_SSH_USERNAME --repo $REPO --body $envVars['STAGING_SSH_USERNAME']
    gh secret set STAGING_SSH_PASSWORD --repo $REPO --body $envVars['STAGING_SSH_PASSWORD']
    gh secret set STAGING_SSH_PORT --repo $REPO --body $envVars['STAGING_SSH_PORT']
    gh secret set STAGING_DEPLOY_PATH --repo $REPO --body $envVars['STAGING_DEPLOY_PATH']
    gh secret set STAGING_BACKUP_PATH --repo $REPO --body $envVars['STAGING_BACKUP_PATH']
    Write-Host "✅ SSH configuration set from .env.staging" -ForegroundColor Green
} else {
    Write-Host "⚠️ SSH configuration not found in .env.staging - skipping" -ForegroundColor Yellow
}

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
if ($envVars['DEBUG']) {
    gh secret set STAGING_DEBUG --repo $REPO --body $envVars['DEBUG']
    gh secret set STAGING_SECRET_KEY --repo $REPO --body $envVars['SECRET_KEY']
    gh secret set STAGING_APP_PORT --repo $REPO --body $envVars['APP_PORT']
    gh secret set STAGING_TIME_ZONE --repo $REPO --body $envVars['TIME_ZONE']
    Write-Host "✅ Django configuration set from .env.staging" -ForegroundColor Green
} else {
    Write-Host "⚠️ Django configuration not found in .env.staging - skipping" -ForegroundColor Yellow
}

# === Database Configuration ===
Write-Host "🗄️ Setting Database Configuration..." -ForegroundColor Cyan
if ($envVars['DB_ENGINE']) {
    gh secret set STAGING_DB_ENGINE --repo $REPO --body $envVars['DB_ENGINE']
    gh secret set STAGING_DB_NAME --repo $REPO --body $envVars['DB_NAME']
    gh secret set STAGING_DB_USER --repo $REPO --body $envVars['DB_USER']
    gh secret set STAGING_DB_PASSWORD --repo $REPO --body $envVars['DB_PASSWORD']
    gh secret set STAGING_DB_HOST --repo $REPO --body $envVars['DB_HOST']
    gh secret set STAGING_DB_PORT --repo $REPO --body $envVars['DB_PORT']
    Write-Host "✅ Database configuration set from .env.staging" -ForegroundColor Green
} else {
    Write-Host "⚠️ Database configuration not found in .env.staging - skipping" -ForegroundColor Yellow
}

# === Domain and Security ===
Write-Host "🔒 Setting Domain and Security Configuration..." -ForegroundColor Cyan
if ($envVars['ALLOWED_HOSTS']) {
    gh secret set STAGING_ALLOWED_HOSTS --repo $REPO --body $envVars['ALLOWED_HOSTS']
    gh secret set STAGING_CSRF_TRUSTED_ORIGINS --repo $REPO --body $envVars['CSRF_TRUSTED_ORIGINS']
    Write-Host "✅ Domain and security configuration set from .env.staging" -ForegroundColor Green
} else {
    Write-Host "⚠️ Domain configuration not found in .env.staging - skipping" -ForegroundColor Yellow
}

# === CORS Configuration ===
Write-Host "🌐 Setting CORS Configuration..." -ForegroundColor Cyan
if ($envVars['CORS_ALLOW_ALL_ORIGINS']) {
    gh secret set STAGING_CORS_ALLOW_ALL_ORIGINS --repo $REPO --body $envVars['CORS_ALLOW_ALL_ORIGINS']
    Write-Host "✅ CORS configuration set from .env.staging" -ForegroundColor Green
} else {
    Write-Host "⚠️ CORS configuration not found in .env.staging - skipping" -ForegroundColor Yellow
}

# === Email Configuration ===
Write-Host "📧 Setting Email Configuration..." -ForegroundColor Cyan
if ($envVars['EMAIL_BACKEND']) {
    gh secret set STAGING_EMAIL_BACKEND --repo $REPO --body $envVars['EMAIL_BACKEND']
    gh secret set STAGING_EMAIL_HOST --repo $REPO --body $envVars['EMAIL_HOST']
    gh secret set STAGING_EMAIL_PORT --repo $REPO --body $envVars['EMAIL_PORT']
    gh secret set STAGING_EMAIL_USE_TLS --repo $REPO --body $envVars['EMAIL_USE_TLS']
    gh secret set STAGING_EMAIL_USE_SSL --repo $REPO --body $envVars['EMAIL_USE_SSL']
    gh secret set STAGING_EMAIL_HOST_USER --repo $REPO --body $envVars['EMAIL_HOST_USER']
    gh secret set STAGING_EMAIL_HOST_PASSWORD --repo $REPO --body $envVars['EMAIL_HOST_PASSWORD']
    gh secret set STAGING_DEFAULT_FROM_EMAIL --repo $REPO --body $envVars['DEFAULT_FROM_EMAIL']
    Write-Host "✅ Email configuration set from .env.staging" -ForegroundColor Green
} else {
    Write-Host "⚠️ Email configuration not found in .env.staging - skipping" -ForegroundColor Yellow
}

# === Static and Media Files ===
Write-Host "📁 Setting Static and Media Files Configuration..." -ForegroundColor Cyan
if ($envVars['STATIC_URL']) {
    gh secret set STAGING_STATIC_URL --repo $REPO --body $envVars['STATIC_URL']
    gh secret set STAGING_STATIC_ROOT --repo $REPO --body $envVars['STATIC_ROOT']
    gh secret set STAGING_MEDIA_URL --repo $REPO --body $envVars['MEDIA_URL']
    gh secret set STAGING_MEDIA_ROOT --repo $REPO --body $envVars['MEDIA_ROOT']
    Write-Host "✅ Static and media files configuration set from .env.staging" -ForegroundColor Green
} else {
    Write-Host "⚠️ Static files configuration not found in .env.staging - skipping" -ForegroundColor Yellow
}

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
if ($envVars['LOG_LEVEL']) {
    gh secret set STAGING_LOG_LEVEL --repo $REPO --body $envVars['LOG_LEVEL']
    Write-Host "✅ Logging configuration set from .env.staging" -ForegroundColor Green
} else {
    Write-Host "⚠️ Logging configuration not found in .env.staging - skipping" -ForegroundColor Yellow
}

# === Google Drive Backup Configuration ===
Write-Host "☁️ Setting Google Drive Backup Configuration..." -ForegroundColor Cyan
# Only set token if it's not empty
if ($envVars['GDRIVE_TOKEN'] -and $envVars['GDRIVE_TOKEN'].Trim() -ne '') {
    gh secret set STAGING_GDRIVE_TOKEN --repo $REPO --body $envVars['GDRIVE_TOKEN']
    Write-Host "✅ Google Drive backup configuration set (with token)" -ForegroundColor Green
} else {
    Write-Host "ℹ️ GDRIVE_TOKEN is empty - run scripts/rclone-authorize.ps1 to obtain token" -ForegroundColor Yellow
}

# Set root folder ID if provided
if ($envVars['GDRIVE_ROOT_FOLDER_ID'] -and $envVars['GDRIVE_ROOT_FOLDER_ID'].Trim() -ne '') {
    gh secret set STAGING_GDRIVE_ROOT_FOLDER_ID --repo $REPO --body $envVars['GDRIVE_ROOT_FOLDER_ID']
    Write-Host "✅ Google Drive root folder ID set" -ForegroundColor Green
}

# === Backup Encryption Configuration (Optional) ===
Write-Host "🔐 Setting Backup Encryption Configuration..." -ForegroundColor Cyan
if ($envVars['RESTIC_PASSWORD'] -and $envVars['RESTIC_PASSWORD'].Trim() -ne '') {
    gh secret set STAGING_RESTIC_PASSWORD --repo $REPO --body $envVars['RESTIC_PASSWORD']
    Write-Host "✅ Backup encryption enabled (RESTIC_PASSWORD set)" -ForegroundColor Green
} else {
    Write-Host "ℹ️ RESTIC_PASSWORD not set - backups will be unencrypted" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "✅ All secrets have been configured!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Next steps:" -ForegroundColor Yellow
Write-Host "   1. Create a 'staging' branch if it doesn't exist" -ForegroundColor Gray
Write-Host "   2. Push to the staging branch to trigger deployment" -ForegroundColor Gray
Write-Host "   3. Monitor the GitHub Actions workflow" -ForegroundColor Gray
Write-Host ""
Write-Host "📦 Backup setup:" -ForegroundColor Yellow
Write-Host "   1. If GDRIVE_TOKEN is empty, run: .\scripts\rclone-authorize.ps1" -ForegroundColor Gray
Write-Host "   2. After deployment, initialize backup repo:" -ForegroundColor Gray
Write-Host "      ssh $($envVars['STAGING_SSH_USERNAME'])@$($envVars['STAGING_SSH_HOST'])" -ForegroundColor Gray
Write-Host "      cd $($envVars['STAGING_DEPLOY_PATH'])" -ForegroundColor Gray
Write-Host "      docker compose exec backup /scripts/init-backup-repo.sh" -ForegroundColor Gray
Write-Host ""
if ($envVars['STAGING_SSH_HOST'] -and $envVars['APP_PORT']) {
    Write-Host "🌐 Application will be available at: http://$($envVars['STAGING_SSH_HOST']):$($envVars['APP_PORT'])" -ForegroundColor Cyan
}
