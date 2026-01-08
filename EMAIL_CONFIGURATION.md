# Email Configuration Guide

## Overview
This HRMS system has been configured with **mandatory email routing** to ensure all critical communications are properly tracked and managed.

## Mandatory Email Configuration

### 1. Birthday & Work Anniversary Emails

**All birthday and work anniversary emails are sent from: `hrms@petabytz.com`**

- ✅ **Birthday wishes** are sent directly to the employee from `hrms@petabytz.com`
- ✅ **Birthday announcements** are sent to all other employees from `hrms@petabytz.com`
- ✅ **Work anniversary wishes** are sent directly to the employee from `hrms@petabytz.com`
- ✅ **Work anniversary announcements** are sent to all other employees from `hrms@petabytz.com`

### 2. Leave Request Emails

**All leave requests are sent to: `hrms@petabytz.com` + Reporting Manager**

When an employee submits a leave request:
- ✅ **MANDATORY**: `hrms@petabytz.com` receives the notification
- ✅ **Reporting Manager** (if assigned) receives the notification
- ✅ **Employee** receives an acknowledgment email

### 3. Regularization Request Emails

**All regularization requests are sent to: `hrms@petabytz.com` + Reporting Manager**

When an employee submits an attendance regularization request:
- ✅ **MANDATORY**: `hrms@petabytz.com` receives the notification
- ✅ **Reporting Manager** (if assigned) receives the notification
- ✅ **Employee** receives an acknowledgment email

## Environment Variable Setup

### Required Environment Variable

Add this to your `.env` file:

```bash
# MANDATORY: Petabytz HR Email Configuration
PETABYTZ_HR_EMAIL_PASSWORD=your-actual-password-here
```

### For Production Deployment

1. **On your production server**, set the environment variable:
   ```bash
   export PETABYTZ_HR_EMAIL_PASSWORD="your-actual-password"
   ```

2. **For Docker deployments**, add to your `docker-compose.yml`:
   ```yaml
   environment:
     - PETABYTZ_HR_EMAIL_PASSWORD=your-actual-password
   ```

3. **For Azure/AWS/Cloud deployments**, add as an environment variable in your hosting platform's configuration panel.

## Email Credentials

The system uses the following SMTP configuration for `hrms@petabytz.com`:

- **SMTP Host**: `smtp.office365.com`
- **SMTP Port**: `587`
- **Use TLS**: `True`
- **Username**: `hrms@petabytz.com`
- **Password**: Stored in `PETABYTZ_HR_EMAIL_PASSWORD` environment variable

## How It Works

### Code Implementation

The email functions in `core/email_utils.py` have been hardcoded to use `hrms@petabytz.com`:

```python
# MANDATORY: Use hrms@petabytz.com for all emails
from_email = 'Petabytz HR <hrms@petabytz.com>'

# Get connection for hrms@petabytz.com
connection = get_connection(
    backend='django.core.mail.backends.smtp.EmailBackend',
    host='smtp.office365.com',
    port=587,
    use_tls=True,
    username='hrms@petabytz.com',
    password=env('PETABYTZ_HR_EMAIL_PASSWORD', default=''),
    fail_silently=False,
)
```

### Functions Updated

The following functions have been updated to use `hrms@petabytz.com`:

1. ✅ `send_birthday_email()` - Sends birthday wishes to employee
2. ✅ `send_anniversary_email()` - Sends work anniversary wishes to employee
3. ✅ `send_birthday_announcement()` - Announces birthday to all employees
4. ✅ `send_anniversary_announcement()` - Announces work anniversary to all employees
5. ✅ `send_leave_request_notification()` - Sends leave requests to HR + manager
6. ✅ `send_regularization_request_notification()` - Sends regularization requests to HR + manager

## Testing

To test the email configuration:

1. **Test Birthday Email**:
   ```bash
   python manage.py send_birthday_anniversary_emails --test
   ```

2. **Submit a Leave Request** through the employee portal and verify:
   - `hrms@petabytz.com` receives the email
   - Reporting manager receives the email (if assigned)
   - Employee receives acknowledgment

3. **Submit a Regularization Request** and verify the same recipients

## Deployment Checklist

Before deploying to production:

- [ ] Set `PETABYTZ_HR_EMAIL_PASSWORD` environment variable
- [ ] Verify `hrms@petabytz.com` email account is active
- [ ] Test email sending with `python manage.py send_birthday_anniversary_emails --test`
- [ ] Verify SMTP credentials are correct
- [ ] Check that Office 365 allows SMTP authentication for `hrms@petabytz.com`

## Troubleshooting

### Email Not Sending

1. **Check environment variable**:
   ```bash
   echo $PETABYTZ_HR_EMAIL_PASSWORD
   ```

2. **Check Django logs** for email errors:
   ```bash
   tail -f /path/to/django.log
   ```

3. **Verify SMTP credentials** by testing manually:
   ```python
   python manage.py shell
   >>> from django.core.mail import send_mail
   >>> send_mail('Test', 'Test message', 'hrms@petabytz.com', ['test@example.com'])
   ```

### Common Issues

- **Authentication Failed**: Verify `PETABYTZ_HR_EMAIL_PASSWORD` is correct
- **Connection Timeout**: Check firewall settings for port 587
- **TLS Error**: Ensure `EMAIL_USE_TLS=True` in settings

## Security Notes

⚠️ **IMPORTANT**: 
- Never commit the `.env` file to Git
- Use environment variables for production
- Rotate passwords regularly
- Use app-specific passwords for Office 365 if 2FA is enabled

## Support

For issues or questions about email configuration, contact:
- Technical Support: IT Team
- Email Configuration: System Administrator
