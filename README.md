# HRMS PBS - Human Resource Management System

A comprehensive Django-based Human Resource Management System with AI-powered features for modern workforce management.

## 🚀 Features

### Core HR Modules
- **Employee Management**: Complete employee lifecycle management from onboarding to exit
- **Attendance Tracking**: Real-time attendance with clock-in/clock-out, regularization requests
- **Leave Management**: Multi-type leave system with approval workflows
- **Shift Management**: Flexible shift scheduling with grace periods and late login tracking
- **Payroll Integration**: Employee salary management and bulk import capabilities

### AI-Powered Features
- **HR Chatbot**: Intelligent conversational assistant for HR queries with role-based responses
- **Resume Parser**: Automated resume parsing with AI-powered data extraction
- **Attrition Risk Predictor**: ML-based employee attrition risk analysis
- **Smart Notifications**: Automated email notifications for HR events

### Role-Based Portals
- **Admin Dashboard**: Complete system oversight and management
- **Manager Portal**: Team management, leave approvals, attendance monitoring
- **Employee Portal**: Self-service portal for attendance, leaves, and profile management

### Additional Features
- **Multi-step Employee Onboarding**: Streamlined employee registration process
- **Emergency Contact Management**: Store and manage employee emergency contacts
- **Job History Tracking**: Complete employment history and role changes
- **Document Management**: Employee ID proofs and document storage
- **Exit Management**: Employee exit process with feedback collection

## 🛠️ Technology Stack

- **Backend**: Django 4.x
- **Database**: SQLite (Development) / PostgreSQL (Production Ready)
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5
- **AI/ML**: Google Generative AI (Gemini), Custom ML Models
- **Task Scheduling**: Windows Task Scheduler / Celery (configurable)

## 📋 Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Virtual environment (recommended)
- Git

## 🔧 Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd HRMS_PBS
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   - Create a `.env` file in the root directory
   - Add the following variables:
     ```
     SECRET_KEY=your-secret-key-here
     DEBUG=True
     GEMINI_API_KEY=your-gemini-api-key
     EMAIL_HOST_USER=your-email@gmail.com
     EMAIL_HOST_PASSWORD=your-app-password
     ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Collect static files**
   ```bash
   python manage.py collectstatic
   ```

8. **Run the development server**
   ```bash
   python manage.py runserver
   ```

9. **Access the application**
   - Open your browser and navigate to `http://127.0.0.1:8000`
   - Admin panel: `http://127.0.0.1:8000/admin`

## 📁 Project Structure

```
HRMS_PBS/
├── ai_assistant/          # AI features (chatbot, resume parser, attrition predictor)
├── core/                  # Core app (dashboards, authentication)
├── employees/             # Employee management module
├── hrms/                  # Project settings and configuration
├── media/                 # User-uploaded files
├── static/                # Static files (CSS, JS, images)
├── templates/             # Global templates
├── manage.py              # Django management script
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## 🔐 Default User Roles

The system supports three main user roles:
- **COMPANY_ADMIN**: Full system access
- **MANAGER**: Team management and approval capabilities
- **EMPLOYEE**: Self-service portal access

## 🤖 AI Features Setup

### HR Chatbot
- Requires Google Gemini API key
- Supports role-based queries (Admin, Manager, Employee)
- Real-time HRMS data integration

### Resume Parser
- Upload resumes in PDF/DOCX format
- Automatic extraction of skills, education, experience
- AI-powered data normalization

### Attrition Risk Predictor
- ML-based risk scoring
- Actionable insights and recommendations
- Historical trend analysis

## 📧 Email Notifications

Configure email settings in `.env`:
- Birthday wishes
- Leave approvals/rejections
- Attendance alerts
- System notifications

## 🔄 Task Scheduling

For automated tasks (email notifications, reports):
- **Windows**: Use `setup_task_scheduler.ps1`
- **Linux/macOS**: Configure cron jobs or use Celery

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 Development Workflow

1. Always create a new branch for your feature/fix
2. Write clear commit messages
3. Test thoroughly before pushing
4. Create pull requests for code review
5. Keep your branch updated with main

## 🐛 Known Issues

- Ensure `.env` file is properly configured before running
- Some AI features require active internet connection
- Email notifications require valid SMTP credentials

## 📄 License

This project is proprietary software. All rights reserved.

## 👥 Authors

- **Sathinat Padhi** - Initial work and development

## 🙏 Acknowledgments

- Django community for excellent documentation
- Google Generative AI for chatbot capabilities
- Bootstrap team for UI components

## 📞 Support

For support, email sathinathpadhi2001@gmail.com or create an issue in the repository.

---

**Note**: This is an active development project. Features and documentation are continuously updated.
