from django.contrib.auth.forms import AuthenticationForm


class LoginForm(AuthenticationForm):
    def clean_username(self):
        username = self.cleaned_data.get("username")
        if username:
            username = username.lower()
        return username
