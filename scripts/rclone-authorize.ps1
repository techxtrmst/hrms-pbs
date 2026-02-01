# =============================================================================
# HRMS-PBS rclone Google Drive Authorization Script
# =============================================================================
# This script helps obtain an OAuth token for Google Drive on a
# machine with a browser, which can then be used on the headless staging server.
#
# Prerequisites:
#   1. rclone installed (winget install rclone.rclone)
#   2. GitHub CLI installed and authenticated (gh auth login)
#
# Usage:
#   1. Run this script on a Windows machine with a browser
#   2. Sign in to your Google account when prompted
#   3. Token is automatically pushed to GitHub Secrets
#
# Options:
#   -SkipGitHub     Skip automatic GitHub secret update
#   -SkipTest       Skip Google Drive connection test
# =============================================================================

param(
    [string]$Repo = "techxtrmst/hrms-pbs",
    [switch]$SkipGitHub = $false,
    [switch]$SkipTest = $false
)

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  HRMS-PBS Google Drive Authorization" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# Check if rclone is installed
if (-not (Get-Command rclone -ErrorAction SilentlyContinue)) {
    Write-Host "❌ rclone is not installed!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Install rclone using one of these methods:" -ForegroundColor Yellow
    Write-Host "  winget install rclone.rclone" -ForegroundColor Gray
    Write-Host "  choco install rclone" -ForegroundColor Gray
    Write-Host "  scoop install rclone" -ForegroundColor Gray
    Write-Host ""
    exit 1
}

Write-Host "✅ rclone is installed" -ForegroundColor Green

# Check if GitHub CLI is installed (for automatic secret update)
$ghAvailable = $false
if (-not $SkipGitHub) {
    if (Get-Command gh -ErrorAction SilentlyContinue) {
        $authStatus = gh auth status 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ GitHub CLI authenticated" -ForegroundColor Green
            $ghAvailable = $true
        } else {
            Write-Host "⚠️ GitHub CLI not authenticated - will skip automatic secret update" -ForegroundColor Yellow
            Write-Host "   Run 'gh auth login' to enable automatic secret updates" -ForegroundColor Gray
        }
    } else {
        Write-Host "⚠️ GitHub CLI not installed - will skip automatic secret update" -ForegroundColor Yellow
        Write-Host "   Install with: winget install GitHub.cli" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "📋 Configuration:" -ForegroundColor Yellow
Write-Host "   Repository: $Repo" -ForegroundColor Gray
Write-Host "   Auto-push:  $(if ($ghAvailable -and -not $SkipGitHub) { 'Enabled' } else { 'Disabled' })" -ForegroundColor Gray
Write-Host ""

Write-Host "🔐 Starting OAuth authorization..." -ForegroundColor Cyan
Write-Host ""
Write-Host "A browser window will open. Please:" -ForegroundColor Yellow
Write-Host "  1. Sign in with your Google account" -ForegroundColor Gray
Write-Host "  2. Grant the requested permissions" -ForegroundColor Gray
Write-Host "  3. Wait for the 'Success' message in browser" -ForegroundColor Gray
Write-Host ""
Write-Host "Press Enter to continue..." -ForegroundColor Cyan
Read-Host

Write-Host ""
Write-Host "🌐 Opening browser for Google sign-in..." -ForegroundColor Cyan
Write-Host "(If browser doesn't open, check the URL printed below)" -ForegroundColor Gray
Write-Host ""

# Run rclone authorize for Google Drive
$tokenLine = $null
try {
    $output = & rclone authorize "drive" 2>&1

    # Extract the token JSON from the output
    # rclone outputs the token on a line by itself as a JSON object
    foreach ($line in $output) {
        if ($line -match '^\{.*"access_token".*\}$') {
            $tokenLine = $line
            break
        }
    }

    if (-not $tokenLine) {
        # Try alternate pattern - sometimes token is on multiple lines
        $outputText = $output -join ""
        if ($outputText -match '(\{[^{}]*"access_token"[^{}]*\})') {
            $tokenLine = $matches[1]
        }
    }

} catch {
    Write-Host "❌ Authorization failed: $_" -ForegroundColor Red
    exit 1
}

if (-not $tokenLine) {
    Write-Host ""
    Write-Host "❌ Could not extract token from rclone output" -ForegroundColor Red
    Write-Host ""
    Write-Host "Raw output:" -ForegroundColor Yellow
    $output | ForEach-Object { Write-Host "  $_" }
    Write-Host ""
    Write-Host "Please look for a JSON object containing 'access_token' and set it manually:" -ForegroundColor Yellow
    Write-Host "  gh secret set STAGING_ONEDRIVE_TOKEN --repo $Repo --body '<token>'" -ForegroundColor Gray
    exit 1
}

Write-Host ""
Write-Host "=============================================" -ForegroundColor Green
Write-Host "  Authorization Complete!" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host ""

# Copy to clipboard
try {
    $tokenLine | Set-Clipboard
    Write-Host "✅ Token copied to clipboard" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Could not copy to clipboard" -ForegroundColor Yellow
}

# Show truncated token for verification
$tokenPreview = $tokenLine.Substring(0, [Math]::Min(80, $tokenLine.Length)) + "..."
Write-Host "📋 Token preview: $tokenPreview" -ForegroundColor Gray
Write-Host ""

# =============================================================================
# Test Google Drive Connection
# =============================================================================

if (-not $SkipTest) {
    Write-Host "🔍 Testing Google Drive connection..." -ForegroundColor Cyan

    # Create temporary config for testing
    $testConfig = @"
[gdrive]
type = drive
token = $tokenLine
scope = drive
"@
    $testConfigPath = "$env:TEMP\rclone_test_$([guid]::NewGuid().ToString('N')).conf"
    $testConfig | Out-File -FilePath $testConfigPath -Encoding utf8

    try {
        $listOutput = & rclone --config $testConfigPath lsd gdrive: 2>&1

        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Google Drive connection successful!" -ForegroundColor Green
            Write-Host ""
            Write-Host "Root folders:" -ForegroundColor Yellow
            $listOutput | ForEach-Object { Write-Host "  $_" }
            Write-Host ""
        } else {
            Write-Host "❌ Google Drive connection test failed!" -ForegroundColor Red
            Write-Host $listOutput -ForegroundColor Red
            Write-Host ""
            Write-Host "The token was obtained but connection failed. This might be a permissions issue." -ForegroundColor Yellow
        }
    } finally {
        Remove-Item -Path $testConfigPath -ErrorAction SilentlyContinue
    }
}

# =============================================================================
# Push to GitHub Secrets
# =============================================================================

if ($ghAvailable -and -not $SkipGitHub) {
    Write-Host "☁️ Pushing token to GitHub Secrets..." -ForegroundColor Cyan
    Write-Host "   Repository: $Repo" -ForegroundColor Gray
    Write-Host "   Secret: STAGING_GDRIVE_TOKEN" -ForegroundColor Gray
    Write-Host ""

    try {
        # Use stdin to avoid command line length issues with long tokens
        $tokenLine | gh secret set STAGING_GDRIVE_TOKEN --repo $Repo

        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ GitHub Secret updated successfully!" -ForegroundColor Green
            Write-Host ""
            Write-Host "=============================================" -ForegroundColor Green
            Write-Host "  Setup Complete!" -ForegroundColor Green
            Write-Host "=============================================" -ForegroundColor Green
            Write-Host ""
            Write-Host "The Google Drive token has been saved to GitHub Secrets." -ForegroundColor White
            Write-Host "Your next deployment will include the backup configuration." -ForegroundColor White
            Write-Host ""
            Write-Host "📋 Next steps:" -ForegroundColor Yellow
            Write-Host "   1. Push to staging branch to trigger deployment" -ForegroundColor Gray
            Write-Host "   2. After deployment, initialize backup repository:" -ForegroundColor Gray
            Write-Host "      ssh dev@138.128.242.42" -ForegroundColor Gray
            Write-Host "      cd /var/www/hrms-pbs-staging" -ForegroundColor Gray
            Write-Host "      docker compose exec backup /scripts/init-backup-repo.sh" -ForegroundColor Gray
            Write-Host ""
        } else {
            Write-Host "❌ Failed to update GitHub Secret" -ForegroundColor Red
            Write-Host ""
            Write-Host "Please set the secret manually:" -ForegroundColor Yellow
            Write-Host "  gh secret set STAGING_GDRIVE_TOKEN --repo $Repo" -ForegroundColor Gray
            Write-Host "  (then paste the token and press Ctrl+D)" -ForegroundColor Gray
        }
    } catch {
        Write-Host "❌ Error updating GitHub Secret: $_" -ForegroundColor Red
    }
} else {
    Write-Host ""
    Write-Host "=============================================" -ForegroundColor Cyan
    Write-Host "  Manual Setup Required" -ForegroundColor Cyan
    Write-Host "=============================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Token obtained but automatic GitHub update was skipped." -ForegroundColor White
    Write-Host ""
    Write-Host "To complete setup, run:" -ForegroundColor Yellow
    Write-Host "  gh secret set STAGING_GDRIVE_TOKEN --repo $Repo" -ForegroundColor Gray
    Write-Host "  (paste the token from clipboard and press Ctrl+D)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Or add to .env.staging as GDRIVE_TOKEN and run setup-staging-secrets.ps1" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Done!" -ForegroundColor Green
