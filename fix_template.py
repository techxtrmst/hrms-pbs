import re

# Read the file
file_path = r'd:\PB-Projects\HRMS_PBS\hrms-pbs\employees\templates\employees\employee_list.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the Django template syntax - add spaces around ==
# Pattern: selected_filter=='value' -> selected_filter == 'value'
content = re.sub(r"selected_filter=='([^']+)'", r"selected_filter == '\1'", content)

# Write back
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("File fixed successfully!")
print("Changed all instances of selected_filter=='value' to selected_filter == 'value'")
