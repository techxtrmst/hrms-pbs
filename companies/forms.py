from django import forms
from .models import ShiftSchedule, ShiftBreak


class ShiftScheduleForm(forms.ModelForm):
    class Meta:
        model = ShiftSchedule
        fields = [
            "name",
            "shift_type",
            "start_time",
            "end_time",
            "grace_period_minutes",
            "allowed_late_logins",
            "grace_exceeded_action",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g. Morning Shift"}
            ),
            "shift_type": forms.Select(attrs={"class": "form-select"}),
            "start_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "end_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "grace_period_minutes": forms.NumberInput(attrs={"class": "form-control"}),
            "allowed_late_logins": forms.NumberInput(attrs={"class": "form-control"}),
            "grace_exceeded_action": forms.Select(attrs={"class": "form-select"}),
        }


class ShiftBreakForm(forms.ModelForm):
    class Meta:
        model = ShiftBreak
        fields = ["name", "start_time", "end_time"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control form-control-sm",
                    "placeholder": "Break Name",
                }
            ),
            "start_time": forms.TimeInput(
                attrs={"class": "form-control form-control-sm", "type": "time"}
            ),
            "end_time": forms.TimeInput(
                attrs={"class": "form-control form-control-sm", "type": "time"}
            ),
        }
