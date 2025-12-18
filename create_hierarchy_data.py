import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')
django.setup()

from companies.models import Company
from accounts.models import User
from employees.models import Employee

def create_hierarchy():
    # Ensure Petabytz company
    company = Company.objects.get(name="Petabytz")
    
    # 1. Admin (already exists) - The CEO/HR Head
    try:
        admin_emp = Employee.objects.get(user__username='admin', company=company)
        print(f"Root: {admin_emp}")
    except Employee.DoesNotExist:
        print("Admin employee not found. Please run fix_admin_profile first.")
        return

    # 2. Create Managers
    managers_data = [
        {'name': 'John Engineering', 'role': 'VP Engineering', 'dept': 'Engineering'},
        {'name': 'Sarah Sales', 'role': 'VP Sales', 'dept': 'Sales'},
    ]
    
    managers = []
    for data in managers_data:
        username = data['name'].lower().replace(" ", "")
        user, _ = User.objects.get_or_create(username=username, defaults={
            'first_name': data['name'].split()[0], 
            'last_name': data['name'].split()[1],
            'email': f"{username}@petabytz.com",
            'role': User.Role.MANAGER
        })
        user.set_password('pass123')
        user.company = company
        user.save()
        
        emp, _ = Employee.objects.get_or_create(user=user, defaults={
            'company': company,
            'designation': data['role'],
            'department': data['dept'],
            'manager': admin_emp, # Reporting to Admin
            'badge_id': f"MGR{user.id}"
        })
        managers.append(emp)
        print(f"Created Manager: {emp} -> Reports to {admin_emp}")

    # 3. Create Team Leads (Reporting to Engineering VP - John)
    eng_vp = managers[0]
    leads = []
    
    lead_data = {'name': 'Mike Lead', 'role': 'Tech Lead', 'dept': 'Engineering'}
    username = lead_data['name'].lower().replace(" ", "")
    user, _ = User.objects.get_or_create(username=username, defaults={
        'first_name': 'Mike', 'last_name': 'Lead', 'email': f"{username}@petabytz.com", 'role': User.Role.EMPLOYEE
    })
    user.set_password('pass123')
    user.company = company
    user.save()
    
    lead_emp, _ = Employee.objects.get_or_create(user=user, defaults={
        'company': company,
        'designation': 'Tech Lead',
        'department': 'Engineering',
        'manager': eng_vp,
        'badge_id': f"TL{user.id}"
    })
    print(f"Created Lead: {lead_emp} -> Reports to {eng_vp}")

    # 4. Create Developers (Reporting to Tech Lead)
    devs = ['Alice Dev', 'Bob Dev']
    for name in devs:
        username = name.lower().replace(" ", "")
        user, _ = User.objects.get_or_create(username=username, defaults={
            'first_name': name.split()[0], 'last_name': name.split()[1], 'email': f"{username}@petabytz.com", 'role': User.Role.EMPLOYEE
        })
        user.set_password('pass123')
        user.company = company
        user.save()
        
        dev_emp, _ = Employee.objects.get_or_create(user=user, defaults={
            'company': company,
            'designation': 'Software Engineer',
            'department': 'Engineering',
            'manager': lead_emp,
            'badge_id': f"DEV{user.id}"
        })
        print(f"Created Dev: {dev_emp} -> Reports to {lead_emp}")

    # 5. Create Sales Reps (Reporting to Sales VP - Sarah)
    sales_vp = managers[1]
    sales = ['Tom Sales']
    for name in sales:
        username = name.lower().replace(" ", "")
        user, _ = User.objects.get_or_create(username=username, defaults={
             'first_name': name.split()[0], 'last_name': name.split()[1], 'email': f"{username}@petabytz.com", 'role': User.Role.EMPLOYEE
        })
        user.set_password('pass123')
        user.company = company
        user.save()
        
        rep_emp, _ = Employee.objects.get_or_create(user=user, defaults={
            'company': company,
            'designation': 'Sales Executive',
            'department': 'Sales',
            'manager': sales_vp,
            'badge_id': f"SAL{user.id}"
        })
        print(f"Created Rep: {rep_emp} -> Reports to {sales_vp}")

if __name__ == '__main__':
    create_hierarchy()
