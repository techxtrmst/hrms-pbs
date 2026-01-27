from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from companies.models import Company, ShiftSchedule

from .models import EmergencyContact, Employee, LeaveRequest, RegularizationRequest, LeaveBalance

User = get_user_model()

# Try to import pandas, but make it optional
try:
    import pandas as pd
    import io
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


class EmployeeCreationForm(forms.ModelForm):
    # User fields
    email = forms.EmailField(required=True, label="Official Email")
    first_name = forms.CharField(max_length=30, required=True, label="First Name")
    last_name = forms.CharField(max_length=30, required=True, label="Last Name")

    # Custom Role Selection
    ROLE_CHOICES = [
        ("EMPLOYEE", "Employee"),
        ("MANAGER", "Manager"),
        # Admin role is usually assigned not chosen here, but implementing as requested
        ("COMPANY_ADMIN", "Admin"),
    ]
    role = forms.ChoiceField(choices=ROLE_CHOICES, widget=forms.RadioSelect, initial="EMPLOYEE", label="Role")

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
            "personal_email",
            "mobile_number",
            "gender",
            "marital_status",
            "dob",
            "permanent_address",
            "current_address",
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
            "current_address": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Company Isolation Logic
        if self.user and self.user.role == User.Role.COMPANY_ADMIN:
            # Lock company to admin's company
            self.fields["company_selection"].queryset = Company.objects.filter(pk=self.user.company.id)
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
            self.fields["manager"].label_from_instance = lambda obj: f"{obj.get_full_name()} ({obj.get_role_display()})"

            # Filtering Locations: Only show locations from the same company
            from companies.models import Location

            self.fields["location"].queryset = Location.objects.filter(company=self.user.company, is_active=True)

            # Filtering Shifts
            self.fields["assigned_shift"].queryset = ShiftSchedule.objects.filter(
                company=self.user.company, is_active=True
            )
            self.fields["assigned_shift"].label = "Shift Schedule"

            # Role Configuration: Dynamic Department & Designation
            from companies.models import Department, Designation

            # Departments
            depts = list(Department.objects.filter(company=self.user.company).values_list("name", flat=True))
            if depts:
                # Preserve existing value if not in list
                current_dept = self.instance.department if self.instance and self.instance.pk else None
                if current_dept and current_dept not in depts:
                    depts.append(current_dept)

                dept_choices = [(d, d) for d in depts]
                self.fields["department"] = forms.ChoiceField(
                    choices=dept_choices,
                    widget=forms.Select(attrs={"class": "form-select"}),
                    label="Department",
                )

            # Designations
            desigs = list(Designation.objects.filter(company=self.user.company).values_list("name", flat=True))
            if desigs:
                current_desig = self.instance.designation if self.instance and self.instance.pk else None
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
            raise ValidationError("A user with this email address already exists. Please use a different email.")

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
            "start_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "end_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "leave_type": forms.Select(attrs={"class": "form-select"}),
            "duration": forms.Select(attrs={"class": "form-select"}),
            "reason": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "supporting_document": forms.FileInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        
        # Make required fields mandatory
        self.fields['leave_type'].required = True
        self.fields['start_date'].required = True
        self.fields['end_date'].required = True
        self.fields['reason'].required = True
        
        # Add required attribute to widgets
        self.fields['leave_type'].widget.attrs['required'] = True
        self.fields['start_date'].widget.attrs['required'] = True
        self.fields['end_date'].widget.attrs['required'] = True
        self.fields['reason'].widget.attrs['required'] = True

    def clean(self):
        cleaned_data = super().clean()
        leave_type = cleaned_data.get("leave_type")
        duration = cleaned_data.get("duration")
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        # Validate half-day options are only for single-day leaves
        if duration in ["FIRST_HALF", "SECOND_HALF"]:
            if start_date and end_date and start_date != end_date:
                raise forms.ValidationError(
                    "First Half and Second Half options are only available for single-day leaves. "
                    "Please select the same date for both start and end date."
                )

        return cleaned_data
        # Policy: Bluebix & Softstandard employees can only take SL as Half Day (0.5)
        if self.user and self.user.company:
            company_name = self.user.company.name.lower()
            if "bluebix" in company_name or "softstand" in company_name:
                if leave_type == "SL" and duration != "HALF":
                    raise ValidationError("Company Policy: Sick Leave (SL) can only be taken as Half Day (0.5 days).")

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
        if self.instance.user and User.objects.filter(email=email).exclude(pk=self.instance.user.pk).exists():
            raise ValidationError("A user with this email address already exists. Please use a different email.")
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
            "check_in": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            "check_out": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            "reason": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Reason involves missing punch, system error, etc.",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make all fields required
        self.fields['date'].required = True
        self.fields['check_in'].required = True
        self.fields['check_out'].required = True
        self.fields['reason'].required = True
        
        # Add required attribute to widgets
        self.fields['date'].widget.attrs['required'] = True
        self.fields['check_in'].widget.attrs['required'] = True
        self.fields['check_out'].widget.attrs['required'] = True
        self.fields['reason'].widget.attrs['required'] = True

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
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Full Name"}),
            "phone_number": forms.TextInput(attrs={"class": "form-control", "placeholder": "+91 1234567890"}),
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
            raise ValidationError("Please enter a valid phone number with at least 10 digits.")
        return phone


class BulkLeaveUploadForm(forms.Form):
    """Form for bulk leave balance upload via Excel/CSV"""
    
    upload_file = forms.FileField(
        label="Upload Leave Balance File",
        help_text="Upload Excel (.xlsx) or CSV file with employee leave balances",
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.xlsx,.xls,.csv'
        })
    )
    
    update_mode = forms.ChoiceField(
        choices=[
            ('REPLACE', 'Replace existing balances'),
            ('ADD', 'Add to existing balances'),
            ('UPDATE_ONLY', 'Update only specified fields')
        ],
        initial='REPLACE',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        help_text="Choose how to handle existing leave balances",
        label="Update Mode"
    )
    
    def clean_upload_file(self):
        file = self.cleaned_data.get('upload_file')
        if not file:
            raise ValidationError("Please select a file to upload.")
        
        # Check file extension
        allowed_extensions = ['.xlsx', '.xls', '.csv']
        file_extension = file.name.lower().split('.')[-1]
        if f'.{file_extension}' not in allowed_extensions:
            raise ValidationError("Please upload only Excel (.xlsx, .xls) or CSV files.")
        
        # Check file size (max 5MB)
        if file.size > 5 * 1024 * 1024:
            raise ValidationError("File size should not exceed 5MB.")
        
        return file
    
    def validate_file_content(self, company):
        """Validate the uploaded file content and return processed data"""
        if not PANDAS_AVAILABLE:
            return None, ["Pandas library is not installed. Please install pandas to use bulk upload feature."]
        
        file = self.cleaned_data.get('upload_file')
        if not file:
            return None, ["No file uploaded"]
        
        errors = []
        processed_data = []
        
        try:
            # Read file based on extension
            file_extension = file.name.lower().split('.')[-1]
            
            if file_extension == 'csv':
                df = pd.read_csv(io.BytesIO(file.read()))
            else:  # Excel files
                df = pd.read_excel(io.BytesIO(file.read()))
            
            # Reset file pointer
            file.seek(0)
            
            # Validate required columns
            required_columns = ['employee_id', 'employee_name', 'casual_leave_allocated', 'sick_leave_allocated']
            optional_columns = ['casual_leave_used', 'sick_leave_used', 'carry_forward_leave']
            
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                errors.append(f"Missing required columns: {', '.join(missing_columns)}")
                return None, errors
            
            # Process each row
            for index, row in df.iterrows():
                row_num = index + 2  # Excel row number (accounting for header)
                row_errors = []
                
                # Validate employee
                employee_id = str(row.get('employee_id', '')).strip()
                employee_name = str(row.get('employee_name', '')).strip()
                
                if not employee_id and not employee_name:
                    row_errors.append(f"Row {row_num}: Either employee_id or employee_name is required")
                    continue
                
                # Find employee
                employee = None
                if employee_id:
                    try:
                        employee = Employee.objects.get(
                            badge_id=employee_id, 
                            company=company
                        )
                    except Employee.DoesNotExist:
                        row_errors.append(f"Row {row_num}: Employee with ID '{employee_id}' not found")
                
                if not employee and employee_name:
                    # Try to find by name
                    name_parts = employee_name.split()
                    if len(name_parts) >= 2:
                        try:
                            employee = Employee.objects.get(
                                user__first_name__icontains=name_parts[0],
                                user__last_name__icontains=' '.join(name_parts[1:]),
                                company=company
                            )
                        except (Employee.DoesNotExist, Employee.MultipleObjectsReturned):
                            row_errors.append(f"Row {row_num}: Employee '{employee_name}' not found or multiple matches")
                
                if not employee:
                    errors.extend(row_errors)
                    continue
                
                # Validate numeric fields
                try:
                    casual_allocated = float(row.get('casual_leave_allocated', 0))
                    sick_allocated = float(row.get('sick_leave_allocated', 0))
                    casual_used = float(row.get('casual_leave_used', 0))
                    sick_used = float(row.get('sick_leave_used', 0))
                    carry_forward = float(row.get('carry_forward_leave', 0))
                    
                    # Validate ranges
                    if casual_allocated < 0 or sick_allocated < 0:
                        row_errors.append(f"Row {row_num}: Allocated leaves cannot be negative")
                    
                    if casual_used < 0 or sick_used < 0:
                        row_errors.append(f"Row {row_num}: Used leaves cannot be negative")
                    
                    if casual_used > casual_allocated + carry_forward:
                        row_errors.append(f"Row {row_num}: Casual leave used ({casual_used}) exceeds allocated + carry forward ({casual_allocated + carry_forward})")
                    
                    if sick_used > sick_allocated:
                        row_errors.append(f"Row {row_num}: Sick leave used ({sick_used}) exceeds allocated ({sick_allocated})")
                    
                except (ValueError, TypeError):
                    row_errors.append(f"Row {row_num}: Invalid numeric values for leave balances")
                
                if row_errors:
                    errors.extend(row_errors)
                    continue
                
                # Add to processed data
                processed_data.append({
                    'employee': employee,
                    'employee_id': employee_id,
                    'employee_name': employee_name,
                    'casual_leave_allocated': casual_allocated,
                    'sick_leave_allocated': sick_allocated,
                    'casual_leave_used': casual_used,
                    'sick_leave_used': sick_used,
                    'carry_forward_leave': carry_forward,
                    'row_number': row_num
                })
            
            return processed_data, errors
            
        except Exception as e:
            errors.append(f"Error reading file: {str(e)}")
            return None, errors
