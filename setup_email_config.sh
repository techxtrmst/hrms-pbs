#!/bin/bash

# HRMS Email Configuration Setup Script
# This script helps set up the mandatory email configuration for deployment

echo "=================================================="
echo "HRMS Email Configuration Setup"
echo "=================================================="
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "✅ .env file created"
fi

# Prompt for Petabytz HR email password
echo ""
echo "📧 Configuring hrms@petabytz.com email..."
echo ""
read -sp "Enter password for hrms@petabytz.com: " PETABYTZ_PASSWORD
echo ""

# Check if password is empty
if [ -z "$PETABYTZ_PASSWORD" ]; then
    echo "❌ Password cannot be empty!"
    exit 1
fi

# Update or add PETABYTZ_HR_EMAIL_PASSWORD to .env
if grep -q "PETABYTZ_HR_EMAIL_PASSWORD" .env; then
    # Update existing entry
    sed -i "s/PETABYTZ_HR_EMAIL_PASSWORD=.*/PETABYTZ_HR_EMAIL_PASSWORD=$PETABYTZ_PASSWORD/" .env
    echo "✅ Updated PETABYTZ_HR_EMAIL_PASSWORD in .env"
else
    # Add new entry
    echo "" >> .env
    echo "# MANDATORY: Petabytz HR Email Configuration" >> .env
    echo "PETABYTZ_HR_EMAIL_PASSWORD=$PETABYTZ_PASSWORD" >> .env
    echo "✅ Added PETABYTZ_HR_EMAIL_PASSWORD to .env"
fi

echo ""
echo "=================================================="
echo "Email Configuration Summary"
echo "=================================================="
echo ""
echo "✅ Email Account: hrms@petabytz.com"
echo "✅ SMTP Host: smtp.office365.com"
echo "✅ SMTP Port: 587"
echo "✅ Use TLS: True"
echo ""
echo "📋 Email Routing Configuration:"
echo "   • Birthday/Anniversary emails → FROM hrms@petabytz.com"
echo "   • Leave requests → TO hrms@petabytz.com + Manager"
echo "   • Regularization requests → TO hrms@petabytz.com + Manager"
echo ""
echo "=================================================="
echo "Next Steps"
echo "=================================================="
echo ""
echo "1. Test email configuration:"
echo "   python manage.py send_birthday_anniversary_emails --test"
echo ""
echo "2. Run migrations (if needed):"
echo "   python manage.py migrate"
echo ""
echo "3. Start the server:"
echo "   python manage.py runserver"
echo ""
echo "4. For production deployment:"
echo "   - Set PETABYTZ_HR_EMAIL_PASSWORD as environment variable"
echo "   - Never commit .env file to Git"
echo "   - Use secure password storage (Azure Key Vault, AWS Secrets Manager, etc.)"
echo ""
echo "=================================================="
echo "✅ Email configuration complete!"
echo "=================================================="
