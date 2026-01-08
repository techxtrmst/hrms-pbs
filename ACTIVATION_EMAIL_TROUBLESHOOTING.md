# Activation Email Troubleshooting Guide

## Issue: Activation Emails Not Being Received

### Problem Description
When creating employees manually or through bulk upload for Softstandard or Bluebix companies, activation emails are not being received by the new employees.

### Root Causes & Solutions

#### 1. **Email Configuration Issues**

**Check `.env` file:**
```bash
# Verify these settings exist in your .env file
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.office365.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=hrms@petabytz.com
PETABYTZ_HR_EMAIL_PASSWORD=your_password_here
```

**Solution:**
- Ensure `PETABYTZ_HR_EMAIL_PASSWORD` is set correctly in `.env`
- Restart the Django server after updating `.env`

#### 2. **Email Sending Failures**

**Check Django Logs:**
```bash
# Look for error messages in the console where Django is running
# Search for lines containing "Failed to send activation email"
```

**Common Error Messages:**

**a) SMTPAuthenticationError:**
```
SMTPAuthenticationError: (535, b'5.7.3 Authentication unsuccessful')
```
**Solution:** 
- Verify the email password in `.env` is correct
- Check if the email account (hrms@petabytz.com) is not locked
- Ensure 2FA is not blocking the connection

**b) SMTPConnectError:**
```
SMTPConnectError: (421, b'Service not available')
```
**Solution:**
- Check internet connection
- Verify firewall is not blocking port 587
- Try using port 465 with SSL instead of TLS

**c) SendAsDeniedException:**
```
SendAsDeniedException: User does not have permission to send as this address
```
**Solution:**
- Verify the FROM email address matches the authenticated email
- Check Office 365 "Send As" permissions

#### 3. **Employee Profile Issues**

**Error:** `User has no employee profile`

**Solution:**
- Ensure employee profile is created BEFORE sending activation email
- Check the employee creation order in `multi_step_views.py`:
  1. Create User
  2. Create Employee (with employee_profile)
  3. THEN send activation email

#### 4. **Template Issues**

**Check if template exists:**
```bash
# Verify this file exists:
accounts/templates/accounts/emails/activation_email.html
```

**Solution:**
- Ensure the template file is in the correct location
- Check for syntax errors in the template

### Testing Email Functionality

#### Quick Test Script

Run this in Django shell to test email sending:

```python
python manage.py shell

from django.contrib.auth import get_user_model
from employees.utils import send_activation_email
from django.test import RequestFactory

User = get_user_model()

# Find a test user
user = User.objects.filter(email='test@softstandard.com').first()

# Create mock request
factory = RequestFactory()
request = factory.get('/')
request.META['HTTP_HOST'] = '127.0.0.1:8000'

# Send email
result = send_activation_email(user, request)
print(f"Email sent: {result}")
```

#### Check Email Connection

```python
from core.email_utils import get_hr_email_connection

connection = get_hr_email_connection()
connection.open()
print("✓ Connection successful!")
connection.close()
```

### Enhanced Logging

The system now includes detailed logging for activation emails:

**Log Locations:**
- Console output (where `python manage.py runserver` is running)
- Django logs (if configured)

**Log Messages to Look For:**
```
INFO: Starting activation email process for user: user@example.com
INFO: Token and UID generated successfully for user@example.com
INFO: Activation link generated: http://...
INFO: Email content prepared for user@example.com
INFO: Getting HR email connection for user@example.com
INFO: Creating email object for user@example.com
INFO: Sending activation email to user@example.com from Petabytz HR <hrms@petabytz.com>
INFO: ✓ Activation email sent successfully to user@example.com for company Softstandard
```

**Error Messages:**
```
ERROR: User user@example.com has no employee profile
ERROR: Failed to generate token/UID for user@example.com: ...
ERROR: Failed to send activation email to user@example.com: ...
ERROR: Error type: SMTPAuthenticationError
ERROR: Traceback: ...
```

### Step-by-Step Verification

#### Step 1: Verify Email Configuration
```bash
# Check if .env file exists
ls .env

# Verify email settings (without showing password)
python manage.py shell
>>> from django.conf import settings
>>> print(f"Email Host: {settings.EMAIL_HOST}")
>>> print(f"Email Port: {settings.EMAIL_PORT}")
>>> print(f"Email User: {settings.EMAIL_HOST_USER}")
```

#### Step 2: Test Email Connection
```bash
python manage.py shell
>>> from core.email_utils import get_hr_email_connection
>>> conn = get_hr_email_connection()
>>> conn.open()
>>> conn.close()
>>> print("✓ Email connection works!")
```

#### Step 3: Create Test Employee
1. Go to employee creation page
2. Fill in all required fields
3. Use a valid email address you can access
4. Submit the form
5. Check the Django console for log messages
6. Check the email inbox

#### Step 4: Check Email Delivery
- Check spam/junk folder
- Check if email is blocked by company firewall
- Verify email address is correct
- Check Office 365 admin center for delivery status

### Common Issues by Company

#### Softstandard
- **Issue:** Emails not received
- **Check:** Verify company email domain settings
- **Solution:** Ensure @softstandard.com emails are not blocked

#### Bluebix
- **Issue:** Emails not received
- **Check:** Verify company email domain settings
- **Solution:** Ensure @bluebix.com emails are not blocked

#### Petabytz
- **Issue:** Should work by default
- **Check:** Verify hrms@petabytz.com password is correct

### Fallback Options

If activation emails continue to fail:

1. **Manual Password Distribution:**
   - The system now displays the temporary password when email fails
   - Admin can manually share the password with the employee
   - Password format: `{FirstName}{Last3DigitsOfBadgeID}`

2. **Resend Email Feature:**
   - Use the "Resend Email" button on the employee list page
   - This will regenerate and resend the activation link

3. **Direct Password Reset:**
   - Admin can manually reset password from Django admin
   - Or use the password reset link on the login page

### Prevention

1. **Always test email configuration after deployment**
2. **Monitor Django logs for email errors**
3. **Keep email credentials secure and up-to-date**
4. **Test with different email providers (Gmail, Outlook, etc.)**
5. **Ensure firewall allows outbound SMTP connections**

### Support

If issues persist:
1. Check Django logs for detailed error messages
2. Verify email credentials are correct
3. Test email connection manually
4. Contact IT support to check firewall/network settings
5. Verify Office 365 account status

---

**Last Updated:** January 8, 2026  
**Version:** 2.0 - Enhanced with detailed logging and error handling
