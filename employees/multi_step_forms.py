from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from companies.models import Company, ShiftSchedule

from .models import Employee

User = get_user_model()


class PersonalInfoForm(forms.ModelForm):
    """Step 1: Personal Information"""

    email = forms.EmailField(required=True, label="Official Email")
    personal_email = forms.EmailField(required=False, label="Personal Email", help_text="For information only")
    first_name = forms.CharField(max_length=30, required=True, label="First Name")
    last_name = forms.CharField(max_length=30, required=True, label="Last Name")

    # Custom Role Selection
    ROLE_CHOICES = [
        ("EMPLOYEE", "Employee"),
        ("MANAGER", "Manager"),
        ("COMPANY_ADMIN", "Admin"),
    ]
    role = forms.ChoiceField(choices=ROLE_CHOICES, widget=forms.RadioSelect, initial="EMPLOYEE", label="Role")

    # Company selection
    company_selection = forms.ModelChoiceField(
        queryset=Company.objects.all(),
        widget=forms.RadioSelect,
        required=False,
        label="Company",
    )

    class Meta:
        model = Employee
        fields = [
            "first_name",
            "last_name",
            "pseudo_name",
            "email",
            "personal_email",
            "mobile_number",
            "gender",
            "marital_status",
            "dob",
            "permanent_address",
            "emergency_contact",
            "badge_id",
            "location",
        ]
        widgets = {
            "dob": forms.DateInput(attrs={"type": "date"}),
            "permanent_address": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        self.company_id = kwargs.pop("company_id", None)
        self.location_id = kwargs.pop("location_id", None)
        super().__init__(*args, **kwargs)

        # If company_id and location_id are provided, use them (from step 0)
        if self.company_id and self.location_id:
            from companies.models import Location

            self.company = Company.objects.get(id=self.company_id)
            location = Location.objects.get(id=self.location_id)

            # Set company and location
            self.fields["company_selection"].queryset = Company.objects.filter(pk=self.company.id)
            self.fields["company_selection"].initial = self.company
            self.fields["company_selection"].widget = forms.HiddenInput()

            self.fields["location"].queryset = Location.objects.filter(pk=location.id)
            self.fields["location"].initial = location
            self.fields["location"].widget = forms.HiddenInput()

            return

        # Store company for validation
        self.company = None

        # Company Isolation Logic (fallback for old flow)
        if self.user and self.user.role == User.Role.COMPANY_ADMIN:
            self.fields["company_selection"].queryset = Company.objects.filter(pk=self.user.company.id)
            self.fields["company_selection"].initial = self.user.company
            self.fields["company_selection"].widget.attrs["disabled"] = "disabled"
            self.fields["company_selection"].required = False

            # Filter locations by company
            from companies.models import Location

            self.fields["location"].queryset = Location.objects.filter(company=self.user.company, is_active=True)
            self.fields["location"].required = True
            self.fields["location"].label = "Work Location"

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email:
            email = email.lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email address already exists. Please use a different email.")

        # Domain Validation - use the company from step 0 if available
        company = None

        # Priority 1: Use company from step 0 (self.company set in __init__)
        if hasattr(self, "company") and self.company:
            company = self.company
        # Priority 2: Use company from form selection
        elif self.cleaned_data.get("company_selection"):
            company = self.cleaned_data.get("company_selection")
        # Priority 3: Use logged-in user's company (fallback)
        elif self.user and self.user.company:
            company = self.user.company

        if company and not company.is_email_domain_allowed(email):
            allowed_domains = company.get_allowed_email_domains_list()
            raise ValidationError(
                f"Email domain not allowed. For {company.name}, allowed domains are: {', '.join(allowed_domains)}"
            )

        return email

    def clean(self):
        cleaned_data = super().clean()

        # If company was set from step 0, use that
        if hasattr(self, "company") and self.company:
            cleaned_data["company_selection"] = self.company
            return cleaned_data

        # Manually handle company due to disabled field (old flow)
        if self.user and self.user.role == User.Role.COMPANY_ADMIN:
            cleaned_data["company_selection"] = self.user.company

        if not cleaned_data.get("company_selection"):
            if self.user.is_superuser:
                raise ValidationError("Superusers must select a company.")
            cleaned_data["company_selection"] = self.user.company

        return cleaned_data


class JobDetailsForm(forms.ModelForm):
    """Step 2: Job Profile"""

    designation = forms.ModelChoiceField(
        queryset=Employee.objects.none(),
        required=True,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Designation",
    )

    manager_selection = forms.ModelChoiceField(  # Renamed from manager to avoid conflict
        queryset=Employee.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Reporting Manager",
    )
    department = forms.ModelChoiceField(
        queryset=Employee.objects.none(),
        required=True,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Department",
    )
    shift_schedule = forms.ModelChoiceField(
        queryset=ShiftSchedule.objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Shift Schedule",
    )

    class Meta:
        model = Employee
        fields = [
            "designation",
            "department",
            "work_type",
            "shift_schedule",
            "date_of_joining",  # 'manager' excluded
        ]
        widgets = {
            "date_of_joining": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        company_id = kwargs.pop("company_id", None)
        super().__init__(*args, **kwargs)

        # Get company object from ID
        if company_id:
            from companies.models import Company, Department, Designation

            self.company = Company.objects.get(id=company_id)
        elif self.user and self.user.role == User.Role.COMPANY_ADMIN:
            # Fallback to user's company if not provided explicitly
            self.company = self.user.company
        else:
            self.company = None

        if self.company:
            # Allow cross-company manager assignment
            # Show all eligible managers from all companies
            self.fields["manager_selection"].queryset = Employee.objects.exclude(
                user__role=User.Role.EMPLOYEE
            ).select_related("company", "user")

            # Customize label to show manager name, role, and company
            self.fields["manager_selection"].label_from_instance = lambda obj: (
                f"{obj.user.get_full_name()} ({obj.user.get_role_display()}) - {obj.company.name}"
            )

            # Populate Dynamic Fields
            from companies.models import Department, Designation

            self.fields["designation"].queryset = Designation.objects.filter(company=self.company)
            self.fields["department"].queryset = Department.objects.filter(company=self.company)
            self.fields["shift_schedule"].queryset = ShiftSchedule.objects.filter(company=self.company).order_by("name")

            # Set initial if data comes from session as name/ID
            # The form initialization with 'initial' dict handles basic mapping if keys match.
            # But if session has stored 'names' (strings) from previous runs/edits,
            # we might need to find the object.
            # However, for new flow, it should be fine.
            # If editing (back button), we need to ensure initial data is mapped correctly.

            if "initial" in kwargs:
                initial = kwargs["initial"]

                # Handle designation - can be ID or name
                if initial.get("designation_id"):
                    try:
                        desig = Designation.objects.filter(company=self.company, id=initial["designation_id"]).first()
                        if desig:
                            self.initial["designation"] = desig
                    except Exception:
                        pass
                elif isinstance(initial.get("designation"), str):
                    try:
                        desig = Designation.objects.filter(company=self.company, name=initial["designation"]).first()
                        if desig:
                            self.initial["designation"] = desig
                    except Exception:
                        pass

                # Handle department - can be ID or name
                if initial.get("department_id"):
                    try:
                        dept = Department.objects.filter(company=self.company, id=initial["department_id"]).first()
                        if dept:
                            self.initial["department"] = dept
                    except Exception:
                        pass
                elif isinstance(initial.get("department"), str):
                    try:
                        dept = Department.objects.filter(company=self.company, name=initial["department"]).first()
                        if dept:
                            self.initial["department"] = dept
                    except Exception:
                        pass

                # Handle shift - can be ID or name
                if initial.get("shift_schedule_id"):
                    try:
                        shift = ShiftSchedule.objects.filter(
                            company=self.company, id=initial["shift_schedule_id"]
                        ).first()
                        if shift:
                            self.initial["shift_schedule"] = shift
                    except Exception:
                        pass
                elif isinstance(initial.get("shift_schedule"), str):
                    try:
                        shift = ShiftSchedule.objects.filter(
                            company=self.company, name=initial["shift_schedule"]
                        ).first()
                        if shift:
                            self.initial["shift_schedule"] = shift
                    except Exception:
                        pass


class FinanceDetailsForm(forms.ModelForm):
    """Step 3: Financial Details"""

    ctc_change_reason = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Employee
        fields = [
            "annual_ctc",
            "bank_name",
            "account_number",
            "ifsc_code",
            "uan",
            "pan_number",
            "pf_enabled",
        ]
