
import os

file_path = r'c:\Users\sathi\Downloads\hrms-pbs-main\core\templates\core\base.html'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip_next = False

for i in range(len(lines)):
    if skip_next:
        skip_next = False
        continue

    line = lines[i]
    # Check for the specific split line
    if '{% if years_service > 1' in line and not '%}' in line:
        # found the first half, join it with the next line stripped of leading whitespace
        next_line = lines[i+1].lstrip()
        combined_line = line.rstrip() + ' ' + next_line
        new_lines.append(combined_line)
        skip_next = True
    else:
        new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Fixed split template tag.")
