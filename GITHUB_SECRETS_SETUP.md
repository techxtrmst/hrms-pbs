# GitHub Secrets Setup Guide for Staging Deployment

## Problem
Your GitHub Actions workflow is failing with SSH authentication errors because the required secrets are not configured in your repository.

## Error Messages
```
Error: can't connect without a private SSH key or password
ssh: unable to authenticate, attempted methods [none password], no supported methods remain
```

## Solution: Configure GitHub Repository Secrets

### Step 1: Access GitHub Secrets Settings

1. Go to your GitHub repository: https://github.com/YOUR_USERNAME/YOUR_REPO
2. Click on **Settings** (top menu)
3. In the left sidebar, click **Secrets and variables** → **Actions**
4. Click **New repository secret** for each secret below

### Step 2: Required SSH Connection Secrets

Add these secrets first (CRITICAL for deployment to work):

| Secret Name | Description | Example |
|------------|-------------|---------|
| `STAGING_SSH_HOST` | Your staging server IP or hostname | `192.168.1.100` or `staging.example.com` |
| `STAGING_SSH_USERNAME` | SSH username for the server | `ubuntu`, `root`, or your username |
| `STAGING_SSH_KEY` | Your private SSH key (entire content) | See instructions below |
| `STAGING_SSH_PORT` | SSH port (usually 22) | `22` |

#### How to Get Your SSH Private Key

On your local machine or server where you have SSH access:

```bash
# For RSA key
cat ~/.ssh/id_rsa

# For ED25519 key (recommended)
cat ~/.ssh/id_ed25519
```

Copy the **ENTIRE** output including the header and footer:
```
-----BEGIN [KEY TYPE] PRIVATE KEY-----
[Your private key content here - multiple lines]
-----END [KEY TYPE] PRIVATE KEY-----
```

⚠️ **Important**: 
- Include the BEGIN and END lines
- Don't add any extra spaces or newlines
- Keep this key secure - it provides access to your server

### Step 3: Required Deployment Path Secrets

| Secret Name | Description | Example |
|------------|-------------|---------|
| `STAGING_DEPLOY_PATH` | Directory where app will be deployed | `/home/ubuntu/hrms-backend` |
| `STAGING_BACKUP_PATH` | Directory for backups | `/home/ubuntu/hrms-backups` |

### Step 4: Required Application Configuration Secrets

| Secret Name | Description | Example |
|------------|-------------|---------|
| `STAGING_DEBUG` | Django DEBUG mode | `False` |
| `STAGING_SECRET_KEY` | Django secret key | Generate with: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `STAGING_APP_PORT` | External port for the app | `8000` |

### Step 5: Required Database Secrets

| Secret Name | Description | Example |
|------------|-------------|---------|
| `STAGING_DB_ENGINE` | Database engine | `django.db.backends.postgresql` |
| `STAGING_DB_NAME` | Database name | `hrms_staging` |
| `STAGING_DB_USER` | Database username | `postgres` |
| `STAGING_DB_PASSWORD` | Database password | `your_secure_password` |
| `STAGING_DB_HOST` | Database host | `db` (for Docker) or `localhost` |
| `STAGING_DB_PORT` | Database port | `5432` |

### Step 6: Required Django Settings Secrets

| Secret Name | Description | Example |
|------------|-------------|---------|
| `STAGING_ALLOWED_HOSTS` | Comma-separated allowed hosts | `staging.example.com,192.168.1.100` |
| `STAGING_CSRF_TRUSTED_ORIGINS` | Comma-separated trusted origins | `http://staging.example.com,http://192.168.1.100:8000` |
| `STAGING_CORS_ALLOW_ALL_ORIGINS` | Allow all CORS origins | `False` |
| `STAGING_TIME_ZONE` | Timezone | `UTC` or `Asia/Kolkata` |

### Step 7: Required Static/Media Files Secrets

| Secret Name | Description | Example |
|------------|-------------|---------|
| `STAGING_STATIC_URL` | Static files URL | `/static/` |
| `STAGING_STATIC_ROOT` | Static files directory | `/app/staticfiles` |
| `STAGING_MEDIA_URL` | Media files URL | `/media/` |
| `STAGING_MEDIA_ROOT` | Media files directory | `/app/media` |

### Step 8: Required Email Configuration Secrets

| Secret Name | Description | Example |
|------------|-------------|---------|
| `STAGING_EMAIL_BACKEND` | Email backend | `django.core.mail.backends.smtp.EmailBackend` |
| `STAGING_EMAIL_HOST` | SMTP host | `smtp.gmail.com` |
| `STAGING_EMAIL_PORT` | SMTP port | `587` |
| `STAGING_EMAIL_USE_TLS` | Use TLS | `True` |
| `STAGING_EMAIL_USE_SSL` | Use SSL | `False` |
| `STAGING_EMAIL_HOST_USER` | Email username | `your-email@gmail.com` |
| `STAGING_EMAIL_HOST_PASSWORD` | Email password/app password | `your_app_password` |
| `STAGING_DEFAULT_FROM_EMAIL` | Default from email | `HRMS Staging <noreply@example.com>` |

### Step 9: Optional Secrets (can be empty)

| Secret Name | Description | Example |
|------------|-------------|---------|
| `STAGING_POSTHOG_API_KEY` | PostHog analytics key | Leave empty if not using |
| `STAGING_POSTHOG_HOST` | PostHog host | `https://app.posthog.com` |
| `STAGING_POSTHOG_ENABLED` | Enable PostHog | `False` |
| `STAGING_LOG_LEVEL` | Logging level | `INFO` |
| `STAGING_GDRIVE_TOKEN` | Google Drive token | Leave empty if not using |
| `STAGING_GDRIVE_ROOT_FOLDER_ID` | Google Drive folder ID | Leave empty if not using |
| `STAGING_RESTIC_PASSWORD` | Restic backup password | Leave empty if not using |
| `STAGING_TEAMS_WEBHOOK_URL` | Microsoft Teams webhook | Leave empty if not using |

## Quick Setup Commands

### Generate Django Secret Key
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Generate SSH Key Pair (if you don't have one)
```bash
ssh-keygen -t ed25519 -C "github-actions-staging"
# Then copy the public key to your server
ssh-copy-id -i ~/.ssh/id_ed25519.pub username@your-server
```

### Test SSH Connection
```bash
ssh -i ~/.ssh/id_ed25519 username@your-server -p 22
```

## Verification

After adding all secrets:

1. Go to **Actions** tab in your GitHub repository
2. Find the failed workflow run
3. Click **Re-run all jobs**
4. Or push a new commit to the `staging` branch

## Troubleshooting

### Still getting SSH errors?
- Verify the SSH key has no extra spaces or newlines
- Ensure the public key is added to `~/.ssh/authorized_keys` on the server
- Check that the username and host are correct
- Verify the SSH port (default is 22)

### Deployment fails after SSH connection works?
- Check that all application secrets are correctly set
- Verify database credentials
- Ensure the deploy and backup paths exist on the server

### Need to update a secret?
1. Go to Settings → Secrets and variables → Actions
2. Click on the secret name
3. Click **Update secret**
4. Enter the new value

## Security Notes

⚠️ **Never commit secrets to your repository**
⚠️ **Use strong passwords for database and Django secret key**
⚠️ **Rotate SSH keys periodically**
⚠️ **Use app-specific passwords for email (not your main password)**

## Next Steps

Once all secrets are configured:
1. Push any changes to the `staging` branch
2. The workflow will automatically trigger
3. Monitor the deployment in the Actions tab
4. Check the logs if any step fails

---

**Need Help?** Check the GitHub Actions logs for specific error messages.
