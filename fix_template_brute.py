import re
import os

file_path = r'c:\Users\sathi\Downloads\HRMS_PBS\employees\templates\employees\employee_form.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Company Selection Radio
# Replace {{ radio.choice_label \n }} with {{ radio.choice_label }}
content = re.sub(r'\{\{\s*radio\.choice_label\s+\}\}', '{{ radio.choice_label }}', content)

# Also explicitly look for the broken lines if regex creates issues with multiline
content = content.replace('{{ radio.choice_label\n                                    }}', '{{ radio.choice_label }}')
content = content.replace('{{\n                                    radio.choice_label }}', '{{ radio.choice_label }}')

# Write back
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed template file.")
