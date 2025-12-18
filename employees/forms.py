from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import Employee
from companies.models import Company

User = get_user_model()

class EmployeeCreationForm(forms.ModelForm):
    # User fields
    email = forms.EmailField(required=True, label="Personal Email (Gmail)")
    first_name = forms.CharField(max_length=30, required=True, label="First Name")
    last_name = forms.CharField(max_length=30, required=True, label="Last Name")
    
    # Custom Role Selection
    ROLE_CHOICES = [
        ('EMPLOYEE', 'Employee'),
        ('MANAGER', 'Manager'),
        # Admin role is usually assigned not chosen here, but implementing as requested
        ('COMPANY_ADMIN', 'Admin') 
    ]
    role = forms.ChoiceField(choices=ROLE_CHOICES, widget=forms.RadioSelect, initial='EMPLOYEE', label="Role")

    # Company selection (Only for superuser or specific use cases)
    # We will handle the "limit to own company" in View/Form init
    company_selection = forms.ModelChoiceField(
        queryset=Company.objects.all(),
        widget=forms.RadioSelect,
        required=False,
        label="Company"
    )

    class Meta:
        model = Employee
        fields = [
            # Personal
            'first_name', 'last_name', 'email', 'mobile_number', 'gender', 'marital_status', 
            'dob', 'permanent_address', 'emergency_contact', 'badge_id',
            # Job
            'designation', 'department', 'manager', 'work_type', 'shift', 'date_of_joining',
            # Finace
            'bank_name', 'account_number', 'ifsc_code', 'uan', 'pf_enabled'
        ]
        widgets = {
            'dob': forms.DateInput(attrs={'type': 'date'}),
            'date_of_joining': forms.DateInput(attrs={'type': 'date'}),
            'permanent_address': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Company Isolation Logic
        if self.user and self.user.role == User.Role.COMPANY_ADMIN:
            # Lock company to admin's company
            self.fields['company_selection'].queryset = Company.objects.filter(pk=self.user.company.id)
            self.fields['company_selection'].initial = self.user.company
            self.fields['company_selection'].widget.attrs['disabled'] = 'disabled'
            self.fields['company_selection'].required = False
        
        # Filtering Managers: Only show managers from the same company
        if self.user and self.user.company:
             # Find employees in this company who are 'MANAGER' or 'COMPANY_ADMIN' role in User model
             # This is a bit complex due to OneToOne reverse relation
             self.fields['manager'].queryset = Employee.objects.filter(
                 company=self.user.company
             ).exclude(user__role=User.Role.EMPLOYEE) # Naive filter

    def clean(self):
        cleaned_data = super().clean()
        
        # Manually handle company due to disabled field
        if self.user and self.user.role == User.Role.COMPANY_ADMIN:
            cleaned_data['company_selection'] = self.user.company
            
        if not cleaned_data.get('company_selection'):
             if self.user.is_superuser:
                 raise ValidationError("Superusers must select a company.")
             cleaned_data['company_selection'] = self.user.company

        return cleaned_data

    def save(self, commit=True):
        cleaned_data = self.cleaned_data
        
        # Logic to generate password: First Name + Last 3 digits of Badge ID
        first_name = cleaned_data['first_name']
        badge_id = cleaned_data['badge_id']
        
        if not badge_id or len(badge_id) < 3:
            password = f"{first_name}123" # Fallback
        else:
            password = f"{first_name}{badge_id[-3:]}"
        
        # 1. Create User
        user = User.objects.create_user(
            username=cleaned_data['email'],
            email=cleaned_data['email'],
            password=password,
            first_name=first_name,
            last_name=cleaned_data['last_name'],
            role=cleaned_data['role'],
            company=cleaned_data['company_selection']
        )
        
        # 2. Create Employee
        employee = super(forms.ModelForm, self).save(commit=False)
        employee.user = user
        employee.company = cleaned_data['company_selection']
        
        if commit:
            employee.save()
        return employee
