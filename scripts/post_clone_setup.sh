#!/bin/bash
# Post-clone setup script
# This script is meant to be run after cloning the repository

echo "=========================================="
echo "HRMS PBS - Post Clone Setup"
echo "=========================================="
echo ""

# Check if pre-commit is installed
if ! command -v pre-commit &> /dev/null; then
    echo "⚠️  Pre-commit not found. Installing..."
    pip install pre-commit
fi

# Check if hooks are installed
if [ ! -f .git/hooks/pre-commit ]; then
    echo "📦 Setting up pre-commit hooks..."
    python scripts/setup_precommit.py
else
    echo "✅ Pre-commit hooks already installed"
fi

# Check if .env exists
if [ ! -f .env ]; then
    echo ""
    echo "⚠️  .env file not found"
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
    echo "✅ .env created. Please update it with your values."
else
    echo "✅ .env file exists"
fi

echo ""
echo "=========================================="
echo "✅ Setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Update .env with your configuration"
echo "  2. Run: python manage.py migrate"
echo "  3. Run: python manage.py createsuperuser"
echo "  4. Run: python manage.py runserver"
echo ""
echo "📚 Documentation:"
echo "  - Quick Start: QUICK_START_PRECOMMIT.md"
echo "  - Full Guide: docs/PRE_COMMIT_HOOKS.md"
echo ""
