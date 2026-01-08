# Email Configuration Changes - Summary

## Date: 2026-01-08

## Overview
The HRMS email system has been reconfigured to ensure all critical emails are routed through `hrms@petabytz.com` as the mandatory sender/recipient.

---

## Changes Made

### 1. **Modified `core/email_utils.py`**

Updated the following functions to use `hrms@petabytz.com`:

#### Birthday & Anniversary Functions
- ✅ `send_birthday_email()` - Now sends FROM `hrms@petabytz.com`
- ✅ `send_anniversary_email()` - Now sends FROM `hrms@petabytz.com`
- ✅ `send_birthday_announcement()` - Now sends FROM `hrms@petabytz.com`
- ✅ `send_anniversary_announcement()` - Now sends FROM `hrms@petabytz.com`

#### Leave & Regularization Functions
- ✅ `send_leave_request_notification()` - Now sends TO `hrms@petabytz.com` + Manager
- ✅ `send_regularization_request_notification()` - Now sends TO `hrms@petabytz.com` + Manager

**Key Changes:**
```python
# OLD CODE (Company-specific email)
connection = get_company_email_connection(employee.company)
if employee.company.hr_email:
    from_email = f'{from_name} <{employee.company.hr_email}>'

# NEW CODE (Mandatory hrms@petabytz.com)
from_email = 'Petabytz HR <hrms@petabytz.com>'
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

### 2. **Updated `.env.example`**

Added new environment variable:
```bash
# MANDATORY: Petabytz HR Email Configuration
# This email (hrms@petabytz.com) is used for ALL birthday/anniversary emails
# and MUST receive ALL leave and regularization requests
PETABYTZ_HR_EMAIL_PASSWORD=your-hrms-petabytz-password
```

### 3. **Created Documentation Files**

- ✅ `EMAIL_CONFIGURATION.md` - Comprehensive email setup guide
- ✅ `setup_email_config.sh` - Bash setup script for Linux/Mac
- ✅ `setup_email_config.ps1` - PowerShell setup script for Windows
- ✅ `EMAIL_CHANGES_SUMMARY.md` - This file

---

## Email Routing Rules

### Birthday Emails
| Email Type | Sender | Recipient(s) |
|------------|--------|--------------|
| Birthday Wish | `hrms@petabytz.com` | Employee (birthday person) |
| Birthday Announcement | `hrms@petabytz.com` | All other employees |

### Work Anniversary Emails
| Email Type | Sender | Recipient(s) |
|------------|--------|--------------|
| Anniversary Wish | `hrms@petabytz.com` | Employee (anniversary person) |
| Anniversary Announcement | `hrms@petabytz.com` | All other employees |

### Leave Request Emails
| Email Type | Sender | Recipient(s) |
|------------|--------|--------------|
| Leave Request Notification | `hrms@petabytz.com` | **MANDATORY**: `hrms@petabytz.com` + Reporting Manager |
| Leave Request Acknowledgment | `hrms@petabytz.com` | Employee (requester) |

### Regularization Request Emails
| Email Type | Sender | Recipient(s) |
|------------|--------|--------------|
| Regularization Notification | `hrms@petabytz.com` | **MANDATORY**: `hrms@petabytz.com` + Reporting Manager |
| Regularization Acknowledgment | `hrms@petabytz.com` | Employee (requester) |

---

## Deployment Requirements

### Environment Variable Setup

**Required for ALL deployments:**

1. **Local Development:**
   ```bash
   # Add to .env file
   PETABYTZ_HR_EMAIL_PASSWORD=your-actual-password
   ```

2. **Production Server:**
   ```bash
   # Set as environment variable
   export PETABYTZ_HR_EMAIL_PASSWORD="your-actual-password"
   ```

3. **Docker Deployment:**
   ```yaml
   # Add to docker-compose.yml
   environment:
     - PETABYTZ_HR_EMAIL_PASSWORD=your-actual-password
   ```

4. **Cloud Deployment (Azure/AWS):**
   - Add `PETABYTZ_HR_EMAIL_PASSWORD` in the platform's environment variables section

---

## Testing Instructions

### 1. Test Birthday/Anniversary Emails
```bash
python manage.py send_birthday_anniversary_emails --test
```

### 2. Test Leave Request Email
1. Log in as an employee
2. Submit a leave request
3. Verify emails received at:
   - ✅ `hrms@petabytz.com`
   - ✅ Reporting manager's email (if assigned)
   - ✅ Employee's email (acknowledgment)

### 3. Test Regularization Request Email
1. Log in as an employee
2. Submit an attendance regularization request
3. Verify emails received at:
   - ✅ `hrms@petabytz.com`
   - ✅ Reporting manager's email (if assigned)
   - ✅ Employee's email (acknowledgment)

---

## Migration Notes

### No Database Changes Required
- ✅ No new migrations needed
- ✅ No database schema changes
- ✅ Only code-level changes

### Backward Compatibility
- ❌ **Not backward compatible** - All emails now MUST use `hrms@petabytz.com`
- ⚠️ Company-specific email settings (`hr_email` in Company model) are no longer used for these email types

---

## Security Considerations

### Password Storage
- ✅ Password stored in environment variable (not in code)
- ✅ `.env` file is gitignored (not committed to repository)
- ✅ Use app-specific password if Office 365 has 2FA enabled

### Recommendations
1. **Rotate passwords regularly** (every 90 days)
2. **Use Azure Key Vault** or **AWS Secrets Manager** for production
3. **Enable email logging** to track all sent emails
4. **Monitor `hrms@petabytz.com` inbox** for delivery failures

---

## Troubleshooting

### Common Issues

#### 1. Email Not Sending
**Symptom:** No emails received
**Solution:**
```bash
# Check environment variable
echo $PETABYTZ_HR_EMAIL_PASSWORD

# Test SMTP connection
python manage.py shell
>>> from django.core.mail import send_mail
>>> send_mail('Test', 'Test', 'hrms@petabytz.com', ['test@example.com'])
```

#### 2. Authentication Failed
**Symptom:** SMTP authentication error
**Solution:**
- Verify `PETABYTZ_HR_EMAIL_PASSWORD` is correct
- Check if Office 365 requires app-specific password
- Ensure account is not locked

#### 3. Connection Timeout
**Symptom:** Timeout connecting to SMTP server
**Solution:**
- Check firewall allows port 587
- Verify network connectivity
- Test with `telnet smtp.office365.com 587`

---

## Rollback Instructions

If you need to revert to company-specific emails:

1. **Restore `core/email_utils.py`** from Git:
   ```bash
   git checkout HEAD -- core/email_utils.py
   ```

2. **Remove environment variable:**
   ```bash
   unset PETABYTZ_HR_EMAIL_PASSWORD
   ```

3. **Restart the application**

---

## Support Contacts

- **Technical Issues:** IT Support Team
- **Email Configuration:** System Administrator
- **Password Reset:** Contact Petabytz IT Admin

---

## Checklist for Deployment

Before deploying to production, ensure:

- [ ] `PETABYTZ_HR_EMAIL_PASSWORD` environment variable is set
- [ ] `hrms@petabytz.com` email account is active and accessible
- [ ] SMTP credentials tested and working
- [ ] Email sending tested with `--test` flag
- [ ] Leave request email tested
- [ ] Regularization request email tested
- [ ] Birthday/anniversary emails tested
- [ ] `.env` file is NOT committed to Git
- [ ] Production environment variables configured
- [ ] Email logging enabled for monitoring

---

## Files Modified

1. ✅ `core/email_utils.py` - Email sending functions
2. ✅ `.env.example` - Environment variable template
3. ✅ `EMAIL_CONFIGURATION.md` - Documentation
4. ✅ `setup_email_config.sh` - Linux/Mac setup script
5. ✅ `setup_email_config.ps1` - Windows setup script
6. ✅ `EMAIL_CHANGES_SUMMARY.md` - This summary

---

## Conclusion

✅ **All email configurations are now mandatory and deployment-ready**

The system will automatically use `hrms@petabytz.com` for all birthday, anniversary, leave, and regularization emails. No manual configuration needed per company - just set the `PETABYTZ_HR_EMAIL_PASSWORD` environment variable and deploy!

**Last Updated:** 2026-01-08
**Version:** 1.0
