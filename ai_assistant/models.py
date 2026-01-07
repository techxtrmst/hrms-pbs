from django.db import models
from django.conf import settings
from employees.models import Employee


class AttritionRisk(models.Model):
    RISK_LEVEL_CHOICES = [
        ("LOW", "Low Risk"),
        ("MEDIUM", "Medium Risk"),
        ("HIGH", "High Risk"),
        ("CRITICAL", "Critical Risk"),
    ]

    employee = models.OneToOneField(
        Employee, on_delete=models.CASCADE, related_name="attrition_risk"
    )
    risk_score = models.FloatField(
        default=0.0, help_text="Calculated risk score (0-100)"
    )
    risk_level = models.CharField(
        max_length=20, choices=RISK_LEVEL_CHOICES, default="LOW"
    )

    # Store reasons as JSON or text
    risk_factors = models.JSONField(
        default=dict, help_text="Factors contributing to risk score"
    )

    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.employee} - {self.risk_level} ({self.risk_score}%)"


class ResumeParsingJob(models.Model):
    """
    Enhanced resume parsing with comprehensive data extraction
    """

    resume = models.FileField(upload_to="resumes/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20, default="PENDING"
    )  # PENDING, PROCESSED, FAILED

    # Basic Details
    parsed_name = models.CharField(max_length=255, null=True, blank=True)
    parsed_email = models.EmailField(null=True, blank=True)
    parsed_phone = models.CharField(max_length=50, null=True, blank=True)
    parsed_location = models.CharField(max_length=255, null=True, blank=True)
    parsed_linkedin = models.URLField(null=True, blank=True)
    parsed_github = models.URLField(null=True, blank=True)
    parsed_portfolio = models.URLField(null=True, blank=True)

    # Skills (Legacy text field + new JSON field)
    parsed_skills = models.TextField(
        null=True, blank=True
    )  # Comma-separated for backward compatibility
    parsed_skills_json = models.JSONField(
        null=True, blank=True
    )  # {"technical": [], "tools": [], "soft": []}

    # Education (JSON Field)
    parsed_education = models.JSONField(null=True, blank=True)
    # Format: [{"degree": "B.Tech", "university": "XYZ", "specialization": "CS", "year": 2020, "gpa": 8.5}]

    # Experience (JSON Field)
    parsed_experience = models.JSONField(null=True, blank=True)
    # Format: [{"company": "ABC", "title": "Developer", "start_date": "2020-01", "end_date": "2022-12", "description": "..."}]
    total_experience_years = models.FloatField(null=True, blank=True)

    # Projects (JSON Field)
    parsed_projects = models.JSONField(null=True, blank=True)
    # Format: [{"title": "E-commerce", "technologies": ["React", "Node"], "description": "...", "domain": "Web"}]

    # Certifications (JSON Field)
    parsed_certifications = models.JSONField(null=True, blank=True)
    # Format: [{"name": "AWS Certified", "issuer": "Amazon", "year": 2021}]

    # Categorization
    candidate_type = models.CharField(
        max_length=20, null=True, blank=True
    )  # FRESHER/EXPERIENCED
    role_fit = models.CharField(
        max_length=100, null=True, blank=True
    )  # Frontend, Backend, etc.
    domain = models.CharField(
        max_length=100, null=True, blank=True
    )  # IT, Finance, etc.

    # Duplicate Detection
    duplicate_check_hash = models.CharField(max_length=64, null=True, blank=True)
    is_duplicate = models.BooleanField(default=False)
    duplicate_of = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL
    )

    def __str__(self):
        return (
            f"Resume {self.id} - {self.parsed_name or 'Unknown'} - {self.uploaded_at}"
        )


class ChatMessage(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_messages"
    )
    user_message = models.TextField()
    bot_response = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]

    def __str__(self):
        return f"Chat by {self.user.username} at {self.timestamp}"
