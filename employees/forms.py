from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import Employee, LeaveRequest, RegularizationRequest, EmergencyContact
from companies.models import Company, ShiftSchedule

User = get_user_model()


class EmployeeCreationForm(forms.ModelForm):
    # User fields
    email = forms.EmailField(required=True, label="Personal Email (Gmail)")
    first_name = forms.CharField(max_length=30, required=True, label="First Name")
    last_name = forms.CharField(max_length=30, required=True, label="Last Name")

    # Custom Role Selection
    ROLE_CHOICES = [
        ("EMPLOYEE", "Employee"),
        ("MANAGER", "Manager"),
        # Admin role is usually assigned not chosen here, but implementing as requested
        ("COMPANY_ADMIN", "Admin"),
    ]
    role = forms.ChoiceField(
        choices=ROLE_CHOICES, widget=forms.RadioSelect, initial="EMPLOYEE", label="Role"
    )

    # Company selection (Only for superuser or specific use cases)
    # We will handle the "limit to own company" in View/Form init
    company_selection = forms.ModelChoiceField(
        queryset=Company.objects.all(),
        widget=forms.RadioSelect,
        required=False,
        label="Company",
    )

    class Meta:
        model = Employee
        fields = [
            # Personal
            "first_name",
            "last_name",
            "email",
            "mobile_number",
            "gender",
            "marital_status",
            "dob",
            "permanent_address",
            "emergency_contact",
            "badge_id",
            # Job
            "designation",
            "department",
            "manager",
            "location",
            "work_type",
            "assigned_shift",
            "date_of_joining",
            # Finace
            "bank_name",
            "account_number",
            "ifsc_code",
            "uan",
            "pf_enabled",
        ]
        widgets = {
            "dob": forms.DateInput(attrs={"type": "date"}),
            "date_of_joining": forms.DateInput(attrs={"type": "date"}),
            "permanent_address": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Company Isolation Logic
        if self.user and self.user.role == User.Role.COMPANY_ADMIN:
            # Lock company to admin's company
            self.fields["company_selection"].queryset = Company.objects.filter(
                pk=self.user.company.id
            )
            self.fields["company_selection"].initial = self.user.company
            self.fields["company_selection"].widget.attrs["disabled"] = "disabled"
            self.fields["company_selection"].required = False

        # Filtering Managers: Only show managers from the same company
        if self.user and self.user.company:
            # Find Users in this company who are 'MANAGER' or 'COMPANY_ADMIN' role
            # Also include SUPERADMIN users
            company_managers = User.objects.filter(
                company=self.user.company,
                role__in=[User.Role.MANAGER, User.Role.COMPANY_ADMIN],
            )
            super_admins = User.objects.filter(role=User.Role.SUPERADMIN)

            self.fields["manager"].queryset = company_managers | super_admins

            # Customize label to show name and role
            self.fields["manager"].label_from_instance = (
                lambda obj: f"{obj.get_full_name()} ({obj.get_role_display()})"
            )

            # Filtering Locations: Only show locations from the same company
            from companies.models import Location

            self.fields["location"].queryset = Location.objects.filter(
                company=self.user.company, is_active=True
            )

            # Filtering Shifts
            self.fields["assigned_shift"].queryset = ShiftSchedule.objects.filter(
                company=self.user.company, is_active=True
            )
            self.fields["assigned_shift"].label = "Shift Schedule"

            # Role Configuration: Dynamic Department & Designation
            from companies.models import Department, Designation

            # Departments
            depts = list(
                Department.objects.filter(company=self.user.company).values_list(
                    "name", flat=True
                )
            )
            if depts:
                # Preserve existing value if not in list
                current_dept = (
                    self.instance.department
                    if self.instance and self.instance.pk
                    else None
                )
                if current_dept and current_dept not in depts:
                    depts.append(current_dept)

                dept_choices = [(d, d) for d in depts]
                self.fields["department"] = forms.ChoiceField(
                    choices=dept_choices,
                    widget=forms.Select(attrs={"class": "form-select"}),
                    label="Department",
                )

            # Designations
            desigs = list(
                Designation.objects.filter(company=self.user.company).values_list(
                    "name", flat=True
                )
            )
            if desigs:
                current_desig = (
                    self.instance.designation
                    if self.instance and self.instance.pk
                    else None
                )
                if current_desig and current_desig not in desigs:
                    desigs.append(current_desig)

                desig_choices = [(d, d) for d in desigs]
                self.fields["designation"] = forms.ChoiceField(
                    choices=desig_choices,
                    widget=forms.Select(attrs={"class": "form-select"}),
                    label="Designation",
                )

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise ValidationError(
                "A user with this email address already exists. Please use a different email."
            )

        # Domain Validation
        company = self.cleaned_data.get("company_selection")
        if not company and self.user and self.user.company:
            company = self.user.company

        if company and not company.is_email_domain_allowed(email):
            allowed_domains = company.get_allowed_email_domains_list()
            raise ValidationError(
                f"Email domain not allowed. For {company.name}, allowed domains are: {', '.join(allowed_domains)}"
            )

        return email

    def clean(self):
        cleaned_data = super().clean()

        # Manually handle company due to disabled field
        if self.user and self.user.role == User.Role.COMPANY_ADMIN:
            cleaned_data["company_selection"] = self.user.company

        if not cleaned_data.get("company_selection"):
            if self.user.is_superuser:
                raise ValidationError("Superusers must select a company.")
            cleaned_data["company_selection"] = self.user.company

        return cleaned_data

    def save(self, commit=True):
        cleaned_data = self.cleaned_data

        # 1. Create User with unusable password (to force setup via email)
        first_name = cleaned_data["first_name"]

        user = User.objects.create_user(
            username=cleaned_data["email"],
            email=cleaned_data["email"],
            password=None,  # Will set unusable password
            first_name=first_name,
            last_name=cleaned_data["last_name"],
            role=cleaned_data["role"],
            company=cleaned_data["company_selection"],
        )
        user.set_unusable_password()
        user.save()

        # 2. Create Employee
        employee = super(forms.ModelForm, self).save(commit=False)
        employee.user = user
        employee.company = cleaned_data["company_selection"]

        if commit:
            employee.save()

            # 3. Send Activation / Welcome Email
            from .utils import send_activation_email

            # We don't have request here easily without hacking kwargs,
            # so we rely on the fallback or refactor view.
            # Given constraints, we just call it.
            send_activation_email(user)

        return employee


class LeaveApplicationForm(forms.ModelForm):
    class Meta:
        model = LeaveRequest
        fields = [
            "leave_type",
            "start_date",
            "end_date",
            "duration",
            "reason",
            "supporting_document",
        ]
        widgets = {
            "start_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "end_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "leave_type": forms.Select(attrs={"class": "form-select"}),
            "duration": forms.RadioSelect(attrs={"class": "form-check-input"}),
            "reason": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "supporting_document": forms.FileInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        leave_type = cleaned_data.get("leave_type")
        duration = cleaned_data.get("duration")

        # Policy: Bluebix & Softstandard employees can only take SL as Half Day (0.5)
        if self.user and self.user.company:
            company_name = self.user.company.name.lower()
            if "bluebix" in company_name or "softstand" in company_name:
                if leave_type == "SL" and duration != "HALF":
                    raise ValidationError(
                        "Company Policy: Sick Leave (SL) can only be taken as Half Day (0.5 days)."
                    )

        return cleaned_data


class EmployeeUpdateForm(EmployeeCreationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Populate User fields from the related User object
            self.fields["first_name"].initial = self.instance.user.first_name
            self.fields["last_name"].initial = self.instance.user.last_name
            self.fields["email"].initial = self.instance.user.email
            self.fields["role"].initial = self.instance.user.role

            # Ensure company selection reflects current state
            self.fields["company_selection"].initial = self.instance.company
            # If manually handling widget attributes in parent, ensure they persist or are updated

    def clean_email(self):
        email = self.cleaned_data.get("email")
        # Check uniqueness excluding current user
        if (
            self.instance.user
            and User.objects.filter(email=email)
            .exclude(pk=self.instance.user.pk)
            .exists()
        ):
            raise ValidationError(
                "A user with this email address already exists. Please use a different email."
            )
        return email

    def save(self, commit=True):
        # We don't call super().save() because parent tries to create a NEW user
        # We want to update the existing user and employee

        employee = super(forms.ModelForm, self).save(commit=False)

        # Update User
        user = employee.user
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        user.username = self.cleaned_data["email"]
        user.role = self.cleaned_data["role"]

        # Update Company if changed (and allowed)
        if self.cleaned_data.get("company_selection"):
            user.company = self.cleaned_data["company_selection"]
            employee.company = self.cleaned_data["company_selection"]

        if commit:
            user.save()
            employee.save()

        return employee


class EmployeeBulkImportForm(forms.Form):
    import_file = forms.FileField(
        label="Upload Excel File",
        help_text="Upload .xlsx file containing employee details. Required columns: First Name, Last Name, Email, Designation, Department, Date of Joining (YYYY-MM-DD), Date of Birth (YYYY-MM-DD).",
    )

    def clean_import_file(self):
        file = self.cleaned_data["import_file"]
        return file


class RegularizationRequestForm(forms.ModelForm):
    class Meta:
        model = RegularizationRequest
        fields = ["date", "check_in", "check_out", "reason"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "check_in": forms.TimeInput(
                attrs={"type": "time", "class": "form-control"}
            ),
            "check_out": forms.TimeInput(
                attrs={"type": "time", "class": "form-control"}
            ),
            "reason": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Reason involves missing punch, system error, etc.",
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        check_in = cleaned_data.get("check_in")
        check_out = cleaned_data.get("check_out")

        if check_in and check_out and check_in >= check_out:
            raise ValidationError("Check-out time must be after check-in time.")

        return cleaned_data


class EmergencyContactForm(forms.ModelForm):
    """Form for managing employee emergency contacts"""

    class Meta:
        model = EmergencyContact
        fields = ["name", "phone_number", "relationship", "is_primary"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Full Name"}
            ),
            "phone_number": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "+91 1234567890"}
            ),
            "relationship": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g., Spouse, Parent, Sibling",
                }
            ),
            "is_primary": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        labels = {
            "name": "Contact Name",
            "phone_number": "Phone Number",
            "relationship": "Relationship",
            "is_primary": "Primary Contact",
        }

    def clean_phone_number(self):
        phone = self.cleaned_data.get("phone_number")
        # Basic validation - you can enhance this
        if phone and len(phone) < 10:
            raise ValidationError(
                "Please enter a valid phone number with at least 10 digits."
            )
        return phone
