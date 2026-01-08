# Quick Setup Instructions

## ⚡ Quick Start (5 Minutes)

### Step 1: Add Email Password to .env

You need to add the password for `hrms@petabytz.com` to your `.env` file.

**Option A: Manual Setup**
1. Open `.env` file in your project root
2. Add this line at the end:
   ```
   PETABYTZ_HR_EMAIL_PASSWORD=your-actual-password-here
   ```
3. Replace `your-actual-password-here` with the actual password for hrms@petabytz.com
4. Save the file

**Option B: Automated Setup (Windows)**
Run the PowerShell script:
```powershell
.\setup_email_config.ps1
```

**Option B: Automated Setup (Linux/Mac)**
Run the bash script:
```bash
chmod +x setup_email_config.sh
./setup_email_config.sh
```

### Step 2: Test the Configuration

Run this command to test if emails work:
```bash
python manage.py send_birthday_anniversary_emails --test
```

### Step 3: Restart Your Server

If your server is running, restart it to load the new environment variable:
```bash
# Stop the current server (Ctrl+C)
# Then start it again:
python manage.py runserver
```

---

## ✅ What's Been Configured

### Birthday & Work Anniversary Emails
- ✅ All emails sent FROM `hrms@petabytz.com`
- ✅ Birthday wishes go to the employee
- ✅ Birthday announcements go to all other employees
- ✅ Same for work anniversaries

### Leave Requests
- ✅ All leave requests sent TO `hrms@petabytz.com` (MANDATORY)
- ✅ Also sent to the employee's reporting manager (if assigned)
- ✅ Employee receives acknowledgment email

### Regularization Requests
- ✅ All regularization requests sent TO `hrms@petabytz.com` (MANDATORY)
- ✅ Also sent to the employee's reporting manager (if assigned)
- ✅ Employee receives acknowledgment email

---

## 🚀 For Production Deployment

When you deploy to production, you need to set the environment variable on your server:

**Azure:**
1. Go to your App Service
2. Settings → Configuration → Application settings
3. Add new setting:
   - Name: `PETABYTZ_HR_EMAIL_PASSWORD`
   - Value: `your-actual-password`

**AWS:**
1. Go to your Elastic Beanstalk or EC2
2. Configuration → Environment properties
3. Add:
   - Key: `PETABYTZ_HR_EMAIL_PASSWORD`
   - Value: `your-actual-password`

**Docker:**
Add to your `docker-compose.yml`:
```yaml
environment:
  - PETABYTZ_HR_EMAIL_PASSWORD=your-actual-password
```

---

## 📚 Need More Details?

See these files for comprehensive documentation:
- `EMAIL_CONFIGURATION.md` - Full configuration guide
- `EMAIL_CHANGES_SUMMARY.md` - Complete list of changes
- `.env.example` - Environment variable template

---

## ⚠️ Important Notes

1. **Never commit `.env` file to Git** - It contains sensitive passwords
2. **Use app-specific password** if Office 365 has 2FA enabled
3. **Test before deploying** - Run the test command first
4. **Monitor the inbox** - Check `hrms@petabytz.com` for delivery issues

---

## 🆘 Troubleshooting

**Emails not sending?**
1. Check if `PETABYTZ_HR_EMAIL_PASSWORD` is set correctly
2. Verify the password is correct for `hrms@petabytz.com`
3. Check Django logs for errors
4. Test SMTP connection manually

**Still having issues?**
See `EMAIL_CONFIGURATION.md` for detailed troubleshooting steps.

---

## ✅ You're All Set!

Once you've added the password to `.env`, the system will automatically:
- Send all birthday/anniversary emails from `hrms@petabytz.com`
- Route all leave requests to `hrms@petabytz.com` + manager
- Route all regularization requests to `hrms@petabytz.com` + manager

**No additional configuration needed!** 🎉
