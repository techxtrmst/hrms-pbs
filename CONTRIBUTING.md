# Contributing to HRMS PBS

Thank you for contributing to HRMS PBS! This document provides guidelines for contributing to the project.

## 🌿 Branching Strategy

We use a feature branch workflow:

- **`main`**: Production-ready code
- **`feature/*`**: New features (e.g., `feature/add-payroll`)
- **`fix/*`**: Bug fixes (e.g., `fix/attendance-calculation`)
- **`update/*`**: Updates to existing features (e.g., `update/chatbot-responses`)

## 📝 Commit Message Guidelines

### Format
```
<type>: <subject>

<body (optional)>
```

### Types
- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, etc.)
- **refactor**: Code refactoring
- **test**: Adding or updating tests
- **chore**: Maintenance tasks

### Examples
```bash
feat: Add employee bulk import feature

fix: Correct attendance calculation for night shifts

docs: Update README with AI features setup

style: Format employee views with Black

refactor: Optimize chatbot query handling

chore: Update dependencies
```

## 🔄 Pull Request Process

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clean, readable code
   - Follow Django best practices
   - Add comments for complex logic

3. **Test your changes**
   - Run the development server
   - Test all affected features
   - Check for console errors

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat: Add your feature description"
   ```

5. **Push to GitHub**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create Pull Request**
   - Go to GitHub repository
   - Click "New Pull Request"
   - Fill in the PR template
   - Request review from team members

7. **Address review comments**
   - Make requested changes
   - Push updates to the same branch
   - Respond to comments

8. **Merge**
   - Once approved, merge the PR
   - Delete the feature branch

## 🧪 Testing Guidelines

Before submitting a PR, ensure:

- [ ] Code runs without errors
- [ ] All features work as expected
- [ ] No console errors in browser
- [ ] Database migrations are included (if applicable)
- [ ] No sensitive data in commits

## 📋 Code Style Guidelines

### Python/Django
- Follow PEP 8 style guide
- Use meaningful variable names
- Add docstrings to functions and classes
- Keep functions focused and small
- Use Django's built-in features when possible

### HTML/Templates
- Use proper indentation (2 or 4 spaces)
- Use Django template tags correctly
- Add comments for complex sections
- Follow Bootstrap conventions

### JavaScript
- Use `const` and `let` instead of `var`
- Use meaningful function names
- Add comments for complex logic
- Handle errors gracefully

### CSS
- Use meaningful class names
- Group related styles
- Use CSS variables for colors
- Keep specificity low

## 🚫 What NOT to Commit

- `.env` files
- Database files (`*.sqlite3`)
- `__pycache__/` directories
- IDE-specific files (`.vscode/`, `.idea/`)
- Media files (unless necessary)
- Log files
- Backup files (`*.bak`)

## 🐛 Reporting Bugs

When reporting bugs, include:

1. **Description**: Clear description of the bug
2. **Steps to Reproduce**: Detailed steps
3. **Expected Behavior**: What should happen
4. **Actual Behavior**: What actually happens
5. **Screenshots**: If applicable
6. **Environment**: OS, browser, Python version

## 💡 Suggesting Features

When suggesting features:

1. **Use Case**: Why is this feature needed?
2. **Description**: What should it do?
3. **Benefits**: How does it improve the system?
4. **Implementation Ideas**: (Optional) How might it work?

## 🤝 Code Review Guidelines

When reviewing code:

- Be respectful and constructive
- Explain why changes are needed
- Suggest improvements, don't just criticize
- Approve when code meets standards
- Test the changes if possible

## 📞 Communication

- **Questions**: Ask in PR comments or team chat
- **Discussions**: Use GitHub Discussions
- **Urgent Issues**: Contact team lead directly

## 🎯 Priority Labels

- **P0 - Critical**: Breaks production, fix immediately
- **P1 - High**: Important feature or major bug
- **P2 - Medium**: Nice to have, not urgent
- **P3 - Low**: Minor improvements

## ✅ Definition of Done

A task is complete when:

- [ ] Code is written and tested
- [ ] Code is reviewed and approved
- [ ] Documentation is updated
- [ ] PR is merged to main
- [ ] Feature is deployed (if applicable)

## 🔐 Security

- Never commit API keys or passwords
- Use environment variables for secrets
- Report security issues privately
- Don't expose sensitive user data

## 📚 Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Python PEP 8](https://pep8.org/)
- [Git Documentation](https://git-scm.com/doc)
- [Bootstrap Documentation](https://getbootstrap.com/docs/)

---

Thank you for contributing to HRMS PBS! Your efforts help make this project better for everyone. 🚀
