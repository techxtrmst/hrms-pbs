import os
import re

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Normalize template tags (collapse multi-line tags)
    def normalize_tag(match):
        tag = match.group(0)
        return re.sub(r'\s+', ' ', tag)

    # 2. Fix filter spacing (e.g., |default: 0 -> |default:0)
    def fix_filter_spacing(match):
        tag = match.group(0)
        tag = re.sub(r'\|\s*(\w+)\s*:', r'|\1:', tag)
        tag = re.sub(r':\s+', r':', tag)
        return tag

    # 3. Fix comparison operator spacing (e.g. x=='y' -> x == 'y')
    def fix_operator_spacing(match):
        tag = match.group(0)
        # Add space around ==, !=, <=, >=, <, > if not already present
        # We look for operators that might be stuck to other characters
        # Note: This is a simple heuristic.
        for op in ['==', '!=', '<=', '>=']:
            tag = re.sub(r'(?<=[^\s!=<>])' + re.escape(op) + r'(?=[^\s!=<>])', f' {op} ', tag)
            tag = re.sub(r'(?<=[^\s!=<>])' + re.escape(op) + r'(?=\s)', f' {op}', tag)
            tag = re.sub(r'(?<=\s)' + re.escape(op) + r'(?=[^\s!=<>])', f'{op} ', tag)
        return tag

    # 3. Remove Git conflict/stash markers
    def remove_git_markers(text):
        # Remove <<<<<<<, =======, >>>>>>> lines
        lines = text.splitlines()
        cleaned_lines = []
        for line in lines:
            if re.match(r'^(<<<<<<<|=======|>>>>>>>)', line.strip()):
                continue
            cleaned_lines.append(line)
        return '\n'.join(cleaned_lines)

    # Apply fixes
    new_content = re.sub(r'\{\{.*?\}\}', normalize_tag, content, flags=re.DOTALL)
    new_content = re.sub(r'\{\{.*?\}\}', fix_filter_spacing, new_content, flags=re.DOTALL)
    new_content = re.sub(r'\{%.*?%\}', normalize_tag, new_content, flags=re.DOTALL)
    new_content = re.sub(r'\{%.*?%\}', fix_filter_spacing, new_content, flags=re.DOTALL)
    new_content = re.sub(r'\{%.*?%\}', fix_operator_spacing, new_content, flags=re.DOTALL)
    
    # Apply Git marker removal
    new_content = remove_git_markers(new_content)

    if content != new_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False

def main():
    fixed_count = 0
    # Walk the entire project directory
    for root, dirs, files in os.walk('.'):
        # Skip certain directories
        if any(skip in root for skip in ['venv', '.git', '__pycache__', 'node_modules']):
            continue
            
        for file in files:
            if file.endswith('.html'):
                filepath = os.path.join(root, file)
                if fix_file(filepath):
                    print(f"Fixed: {filepath}")
                    fixed_count += 1
    
    print(f"\nTotal files fixed: {fixed_count}")

if __name__ == "__main__":
    main()
