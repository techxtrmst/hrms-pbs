# GitHub Deployment and Collaboration Guide

This guide will help you deploy your HRMS_PBS project to GitHub and collaborate with your colleagues.

## 📋 Prerequisites

- [x] Git installed and configured
- [ ] GitHub account created
- [ ] Repository created on GitHub

## 🚀 Step 1: Create a GitHub Repository

1. Go to [GitHub](https://github.com)
2. Click the **"+"** icon in the top right corner
3. Select **"New repository"**
4. Fill in the details:
   - **Repository name**: `HRMS_PBS` (or your preferred name)
   - **Description**: "Human Resource Management System with AI-powered features"
   - **Visibility**: Choose **Private** (recommended for company projects) or **Public**
   - **DO NOT** initialize with README, .gitignore, or license (we already have these)
5. Click **"Create repository"**

## 🔗 Step 2: Connect Your Local Repository to GitHub

After creating the repository, GitHub will show you commands. Use these commands in your terminal:

```bash
# Add the remote repository
git remote add origin https://github.com/YOUR_USERNAME/HRMS_PBS.git

# Verify the remote was added
git remote -v
```

**Replace `YOUR_USERNAME` with your actual GitHub username.**

## 📦 Step 3: Prepare Your First Commit

```bash
# Check current status
git status

# Add all files to staging
git add .

# Create your first commit
git commit -m "Initial commit: HRMS PBS with AI features"
```

## ⬆️ Step 4: Push to GitHub

```bash
# Push to GitHub (first time)
git push -u origin main

# If your default branch is 'master' instead of 'main', use:
# git push -u origin master
```

**Note**: You may be prompted to authenticate. Use your GitHub username and a **Personal Access Token** (not your password).

### Creating a Personal Access Token (if needed):
1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Give it a name like "HRMS_PBS"
4. Select scopes: `repo` (full control of private repositories)
5. Click "Generate token"
6. **Copy the token immediately** (you won't see it again!)
7. Use this token as your password when pushing

## 👥 Step 5: Add Your Colleague as a Collaborator

1. Go to your repository on GitHub
2. Click **"Settings"** tab
3. Click **"Collaborators"** in the left sidebar
4. Click **"Add people"**
5. Enter your colleague's GitHub username or email
6. Click **"Add [username] to this repository"**
7. They will receive an invitation email

## 🌿 Step 6: Branching Strategy for Collaboration

### For You (Main Developer):

```bash
# Always work on a feature branch
git checkout -b feature/your-feature-name

# Make your changes, then:
git add .
git commit -m "Description of your changes"
git push origin feature/your-feature-name
```

### For Your Colleague:

```bash
# Clone the repository (first time only)
git clone https://github.com/YOUR_USERNAME/HRMS_PBS.git
cd HRMS_PBS

# Create their own branch
git checkout -b feature/their-feature-name

# Make changes, then:
git add .
git commit -m "Description of changes"
git push origin feature/their-feature-name
```

## 🔄 Step 7: Creating Pull Requests

### When you or your colleague finish a feature:

1. Go to the repository on GitHub
2. Click **"Pull requests"** tab
3. Click **"New pull request"**
4. Select:
   - **Base**: `main` (the branch you want to merge into)
   - **Compare**: `feature/your-feature-name` (your feature branch)
5. Click **"Create pull request"**
6. Add a title and description
7. Request review from your colleague
8. Click **"Create pull request"**

### Reviewing a Pull Request:

1. Go to **"Pull requests"** tab
2. Click on the pull request to review
3. Review the changes in the **"Files changed"** tab
4. Add comments or approve
5. If approved, click **"Merge pull request"**
6. Click **"Confirm merge"**
7. Optionally delete the feature branch

## 🔄 Step 8: Keeping Your Local Repository Updated

```bash
# Switch to main branch
git checkout main

# Pull latest changes from GitHub
git pull origin main

# Update your feature branch with latest main
git checkout feature/your-feature-name
git merge main
```

## 📝 Daily Workflow

### Starting Work:
```bash
# 1. Update main branch
git checkout main
git pull origin main

# 2. Create or switch to your feature branch
git checkout -b feature/new-feature
# OR
git checkout feature/existing-feature

# 3. Update feature branch with latest main
git merge main
```

### During Work:
```bash
# Save your work frequently
git add .
git commit -m "Descriptive message about what you did"

# Push to GitHub (backup and share)
git push origin feature/your-feature-name
```

### Finishing Work:
```bash
# 1. Commit final changes
git add .
git commit -m "Complete feature: description"

# 2. Push to GitHub
git push origin feature/your-feature-name

# 3. Create Pull Request on GitHub (see Step 7)
```

## ⚠️ Important Best Practices

### 1. **Never commit sensitive data**
   - `.env` file is already in `.gitignore`
   - Never commit API keys, passwords, or secrets
   - Check files before committing

### 2. **Write clear commit messages**
   ```bash
   # Good examples:
   git commit -m "Add employee bulk import feature"
   git commit -m "Fix attendance calculation bug"
   git commit -m "Update chatbot AI responses"
   
   # Bad examples:
   git commit -m "update"
   git commit -m "fix"
   git commit -m "changes"
   ```

### 3. **Pull before you push**
   ```bash
   # Always pull latest changes before pushing
   git pull origin main
   git push origin feature/your-branch
   ```

### 4. **Resolve conflicts carefully**
   - If you get merge conflicts, don't panic
   - Open the conflicting files
   - Look for `<<<<<<<`, `=======`, `>>>>>>>` markers
   - Keep the correct code
   - Remove the markers
   - Commit the resolved files

### 5. **Use meaningful branch names**
   ```bash
   # Good examples:
   feature/add-payroll-module
   fix/attendance-calculation-bug
   update/chatbot-responses
   
   # Bad examples:
   test
   my-branch
   new
   ```

## 🆘 Common Issues and Solutions

### Issue 1: "Permission denied"
**Solution**: Make sure you're added as a collaborator or use your own fork.

### Issue 2: "Merge conflict"
**Solution**: 
```bash
git pull origin main
# Resolve conflicts in files
git add .
git commit -m "Resolve merge conflicts"
git push origin your-branch
```

### Issue 3: "Remote already exists"
**Solution**:
```bash
git remote remove origin
git remote add origin https://github.com/YOUR_USERNAME/HRMS_PBS.git
```

### Issue 4: "Authentication failed"
**Solution**: Use a Personal Access Token instead of your password.

## 📞 Getting Help

- **Git Documentation**: https://git-scm.com/doc
- **GitHub Guides**: https://guides.github.com/
- **Ask your colleague**: Collaboration is about communication!

## 🎯 Quick Reference Commands

```bash
# Check status
git status

# Create new branch
git checkout -b branch-name

# Switch branch
git checkout branch-name

# Add files
git add .                    # Add all files
git add filename.py          # Add specific file

# Commit
git commit -m "message"

# Push
git push origin branch-name

# Pull
git pull origin main

# View branches
git branch

# View remotes
git remote -v

# View commit history
git log --oneline
```

---

**Remember**: Communication is key! Always inform your colleague when you're working on a specific feature to avoid conflicts.

Good luck with your collaboration! 🚀
