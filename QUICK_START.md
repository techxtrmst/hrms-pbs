# 🚀 Quick Start: Deploy to GitHub

Follow these steps to deploy your HRMS_PBS project to GitHub.

## ✅ Step 1: Create GitHub Repository

1. Go to https://github.com
2. Click the **"+"** icon → **"New repository"**
3. Repository name: `HRMS_PBS`
4. Description: `Human Resource Management System with AI-powered features`
5. Choose **Private** or **Public**
6. **DO NOT** check any initialization options
7. Click **"Create repository"**

## ✅ Step 2: Copy Your Repository URL

After creating the repository, GitHub will show you a URL like:
```
https://github.com/YOUR_USERNAME/HRMS_PBS.git
```

**Copy this URL!** You'll need it in the next step.

## ✅ Step 3: Run These Commands

Open your terminal in the project directory and run these commands **one by one**:

### 1. Add the remote repository
```bash
git remote add origin https://github.com/YOUR_USERNAME/HRMS_PBS.git
```
**Replace `YOUR_USERNAME` with your actual GitHub username!**

### 2. Add all files to staging
```bash
git add .
```

### 3. Create your first commit
```bash
git commit -m "Initial commit: HRMS PBS with AI features"
```

### 4. Push to GitHub
```bash
git push -u origin master
```

**Note**: You may be prompted for authentication. Use your GitHub username and a **Personal Access Token** (not your password).

## 🔑 Creating a Personal Access Token (if needed)

If you're asked for a password and it doesn't work:

1. Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click **"Generate new token (classic)"**
3. Name: `HRMS_PBS`
4. Expiration: Choose your preference (90 days recommended)
5. Select scopes: Check **`repo`** (full control of private repositories)
6. Click **"Generate token"**
7. **COPY THE TOKEN IMMEDIATELY** (you won't see it again!)
8. Use this token as your password when Git asks for authentication

## ✅ Step 4: Verify Upload

1. Go to your repository on GitHub
2. Refresh the page
3. You should see all your files!

## 👥 Step 5: Add Your Colleague

1. Go to your repository on GitHub
2. Click **"Settings"** tab
3. Click **"Collaborators"** (left sidebar)
4. Click **"Add people"**
5. Enter your colleague's GitHub username or email
6. Click **"Add [username] to this repository"**

## 📋 Step 6: Share Instructions with Your Colleague

Send them this message:

---

**Hi! I've added you as a collaborator to the HRMS_PBS repository.**

**To get started:**

1. Accept the invitation email from GitHub
2. Clone the repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/HRMS_PBS.git
   cd HRMS_PBS
   ```

3. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. Create a `.env` file with necessary credentials (I'll share separately)

5. Run migrations:
   ```bash
   python manage.py migrate
   ```

6. Start the server:
   ```bash
   python manage.py runserver
   ```

**When working on features:**
- Always create a new branch: `git checkout -b feature/your-feature-name`
- Make changes and commit: `git add .` then `git commit -m "description"`
- Push your branch: `git push origin feature/your-feature-name`
- Create a Pull Request on GitHub for review

See `DEPLOYMENT_GUIDE.md` and `CONTRIBUTING.md` for detailed instructions.

---

## 🎯 Daily Workflow (For Both of You)

### Starting work:
```bash
# Update main branch
git checkout master
git pull origin master

# Create feature branch
git checkout -b feature/your-feature-name
```

### During work:
```bash
# Save changes
git add .
git commit -m "description of changes"
git push origin feature/your-feature-name
```

### Finishing work:
1. Push final changes
2. Go to GitHub
3. Create Pull Request
4. Request review from colleague
5. After approval, merge the PR

## 🆘 Quick Troubleshooting

**Problem**: "remote origin already exists"
```bash
git remote remove origin
git remote add origin https://github.com/YOUR_USERNAME/HRMS_PBS.git
```

**Problem**: "Authentication failed"
- Use Personal Access Token instead of password

**Problem**: "Permission denied"
- Make sure you're using the correct repository URL
- Verify you have write access

**Problem**: "Merge conflict"
```bash
git pull origin master
# Fix conflicts in files
git add .
git commit -m "Resolve merge conflicts"
git push origin your-branch
```

## 📚 Important Files Created

- ✅ `README.md` - Project overview and setup instructions
- ✅ `DEPLOYMENT_GUIDE.md` - Detailed GitHub deployment guide
- ✅ `CONTRIBUTING.md` - Contribution guidelines
- ✅ `.github/PULL_REQUEST_TEMPLATE.md` - PR template
- ✅ `.gitignore` - Files to ignore in Git
- ✅ `requirements.txt` - Python dependencies

## 🎉 You're All Set!

Your project is now ready for collaboration. Remember:
- **Communicate** with your colleague about who's working on what
- **Create branches** for all new features
- **Use Pull Requests** for code review
- **Pull regularly** to stay updated with changes

Good luck! 🚀

---

**Need help?** Check `DEPLOYMENT_GUIDE.md` for detailed instructions.
