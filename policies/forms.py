from django import forms

from .models import Policy, PolicySection


class PolicyForm(forms.ModelForm):
    class Meta:
        model = Policy
        fields = [
            "location",
            "section",
            "title",
            "subtitle",
            "content",
            "version",
            "is_published",
            "effective_date",
            "requires_acknowledgment",
        ]
        widgets = {
            "location": forms.Select(attrs={"class": "form-input"}),
            "section": forms.Select(attrs={"class": "form-input"}),
            "title": forms.TextInput(attrs={"class": "form-input", "placeholder": "e.g. Leave Policy"}),
            "subtitle": forms.TextInput(attrs={"class": "form-input", "placeholder": "Optional subtitle"}),
            "content": forms.Textarea(attrs={"class": "form-input", "rows": 15, "id": "content-editor"}),
            "version": forms.TextInput(attrs={"class": "form-input", "placeholder": "1.0"}),
            "effective_date": forms.DateInput(attrs={"class": "form-input", "type": "date"}),
            "is_published": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "requires_acknowledgment": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Filter locations based on user role
        if user:
            from companies.models import Location

            if user.role == "COMPANY_ADMIN" and user.company:
                # Show all locations for the company, not just admin's location
                self.fields["location"].queryset = Location.objects.filter(company=user.company)
                # Set initial value to admin's location if they have one, but don't restrict the queryset
                if hasattr(user, "employee_profile") and user.employee_profile.location:
                    self.fields["location"].initial = user.employee_profile.location

            # Filter sections by company
            if user.role == "COMPANY_ADMIN" and user.company:
                self.fields["section"].queryset = PolicySection.objects.filter(company=user.company)
