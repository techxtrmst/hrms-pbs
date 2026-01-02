from django.urls import reverse_lazy
from django.contrib.auth.views import PasswordChangeView, LoginView
from django.contrib import messages
import os
from django.conf import settings

class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Define the path to the slides directory
        slides_dir = os.path.join(settings.BASE_DIR, 'static', 'accounts', 'slides')
        
        # List to hold image filenames
        slide_images = []
        
        # Check if directory exists
        if os.path.exists(slides_dir):
            try:
                # Iterate over files in the directory
                for filename in os.listdir(slides_dir):
                    # Check for image extensions
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                        # Add relative path for static tag usage or direct URL construction
                        # We will construct the URL in the template using the static tag logic or just hardcoded path
                        slide_images.append(f"accounts/slides/{filename}")
            except Exception as e:
                print(f"Error reading slides directory: {e}")
        
        # If no images found, fall back to the default ones (handled in template logic)
        context['slide_images'] = slide_images
        return context

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

from django.contrib.auth.views import PasswordResetConfirmView

class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('password_reset_complete')

    def form_valid(self, form):
        response = super().form_valid(form)
        # The form's save method returns the user
        user = form.user
        user.must_change_password = False
        user.save(update_fields=['must_change_password'])
        return response
