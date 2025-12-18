from django.urls import reverse_lazy
from django.contrib.auth.views import PasswordChangeView
from django.contrib import messages

class CustomPasswordChangeView(PasswordChangeView):
    template_name = 'accounts/change_password.html'
    success_url = reverse_lazy('dashboard')  # Redirect to dashboard after success

    def form_valid(self, form):
        # Update the flag - Refetch to be safe from stale objects
        user = self.request.user
        user.must_change_password = False
        user.save(update_fields=['must_change_password'])
        
        print(f"DEBUG: Password changed for {user.email}. Flag set to False.")
        
        # Ensure session auth hash is updated to prevent logout
        from django.contrib.auth import update_session_auth_hash
        update_session_auth_hash(self.request, user)
        
        messages.success(self.request, "Your password has been successfully updated.")
        return super().form_valid(form)
