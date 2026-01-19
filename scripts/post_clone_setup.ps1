# Post-clone setup script for Windows
# This script is meant to be run after cloning the repository

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "HRMS PBS - Post Clone Setup" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if pre-commit is installed
try {
    $null = Get-Command pre-commit -ErrorAction Stop
    Write-Host "[PASS] Pre-commit is installed" -ForegroundColor Green
} catch {
    Write-Host "[INFO] Pre-commit not found. Installing..." -ForegroundColor Yellow
    pip install pre-commit
}

# Check if hooks are installed
if (-not (Test-Path .git\hooks\pre-commit)) {
    Write-Host "[INFO] Setting up pre-commit hooks..." -ForegroundColor Yellow
    python scripts/setup_precommit.py
} else {
    Write-Host "[PASS] Pre-commit hooks already installed" -ForegroundColor Green
}

# Check if .env exists
if (-not (Test-Path .env)) {
    Write-Host ""
    Write-Host "[WARNING] .env file not found" -ForegroundColor Yellow
    Write-Host "[INFO] Creating .env from .env.example..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host "[PASS] .env created. Please update it with your values." -ForegroundColor Green
} else {
    Write-Host "[PASS] .env file exists" -ForegroundColor Green
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "[SUCCESS] Setup complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Update .env with your configuration"
Write-Host "  2. Run: python manage.py migrate"
Write-Host "  3. Run: python manage.py createsuperuser"
Write-Host "  4. Run: python manage.py runserver"
Write-Host ""
Write-Host "Documentation:" -ForegroundColor Yellow
Write-Host "  - Quick Start: QUICK_START_PRECOMMIT.md"
Write-Host "  - Full Guide: docs/PRE_COMMIT_HOOKS.md"
Write-Host ""
