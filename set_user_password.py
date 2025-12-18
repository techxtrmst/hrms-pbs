import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()
target_string = 'rajashekhar.reddy'
new_password = 'password123'

# Try to find the user
users = User.objects.filter(email__icontains=target_string)

if users.count() == 1:
    user = users.first()
    user.set_password(new_password)
    user.save()
    print(f"SUCCESS: Password for user '{user.email}' (ID: {user.id}) has been set to '{new_password}'.")
elif users.count() > 1:
    print(f"ERROR: Multiple users found matching '{target_string}':")
    for u in users:
        print(f" - {u.email} (ID: {u.id})")
    print("Please be more specific.")
else:
    print(f"ERROR: No user found matching '{target_string}'.")
    # Validating all users to see what's there
    print("Listing all users:")
    for u in User.objects.all():
        print(f" - {u.email}")
