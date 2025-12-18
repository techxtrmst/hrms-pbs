import django
from django import forms
from django.conf import settings

if not settings.configured:
    settings.configure(USE_I18N=False)

class F(forms.Form):
    f = forms.ChoiceField(choices=[('1','Option A')], widget=forms.RadioSelect)

print(f"Django Version: {django.get_version()}")
f_inst = F()
bound_field = f_inst['f']
try:
    first_radio = next(iter(bound_field))
    print("Type of yielded object:", type(first_radio))
    print("Attributes:", dir(first_radio))
    if hasattr(first_radio, 'choice_label'):
        print("choice_label:", first_radio.choice_label)
    if hasattr(first_radio, 'label'):
        print("label:", first_radio.label)
except Exception as e:
    print(e)
