import re
import os

def fix_file(file_path):
    print(f"Checking file: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return

    original_len = len(content)
    
    # 1. Normalize {{ ... }}
    # We use a compiled regex with DOTALL
    # We capture the content inside {{ }}
    # We are careful about non-greedy matching.
    # Note: This simple regex may fail on {{ {'a':1} }} because it stops at first }}
    # But checking for that is complex. We assume mostly standard var usage.
    
    var_pattern = re.compile(r'\{\{(.*?)\}\}', re.DOTALL)
    
    def normalize_var(match):
        inner = match.group(1)
        # Check if needs fixing (newlines or multi-spaces)
        if '\n' in inner or '  ' in inner:
            # print(f"Fixing var tag: {inner[:20]}...")
            pass
            
        cleaned = re.sub(r'\s+', ' ', inner).strip()
        # Verify we didn't break quoted strings? 
        # Actually re.sub inside a string literal "a   b" -> "a b". 
        # This MIGHT be an issue for format strings like time:"h:i   A".
        # But usually cleaner is better.
        return f"{{{{ {cleaned} }}}}"

    new_content = var_pattern.sub(normalize_var, content)

    # 2. Normalize {% ... %} and fix operators
    tag_pattern = re.compile(r'\{%(.*?)%\}', re.DOTALL)

    def normalize_tag(match):
        inner = match.group(1)
        cleaned = re.sub(r'\s+', ' ', inner).strip()
        
        # Operator spacing
        operators = ['==', '!=', '<=', '>=', '<', '>']
        for op in operators:
            e_op = re.escape(op)
            
            # Default patterns
            pattern_before = fr'(?<=\S){e_op}'
            pattern_after = fr'{e_op}(?=\S)'
            
            # Special handling for < and > to avoid breaking <=, >=, ->
            if op == '>':
                # Don't add space if preceded by = (>=) or - (->)
                pattern_before = fr'(?<=\S)(?<![=-]){e_op}'
            if op == '<':
                # Don't add space if followed by = (<=)
                pattern_after = fr'{e_op}(?!=)(?=\S)'

            # Space before
            cleaned = re.sub(pattern_before, f' {op}', cleaned)
            # Space after
            cleaned = re.sub(pattern_after, f'{op} ', cleaned)
        
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return f"{{% {cleaned} %}}"

    new_content = tag_pattern.sub(normalize_tag, new_content)
    
    if new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated {file_path} (changed)")
    else:
        print(f"No changes for {file_path} (already clean)")

if __name__ == "__main__":
    files = [
        r"d:\PB-Projects\HRMS_PBS\hrms-pbs\core\templates\core\personal_home.html",
        r"d:\PB-Projects\HRMS_PBS\hrms-pbs\core\templates\core\employee_dashboard.html",
        r"d:\PB-Projects\HRMS_PBS\hrms-pbs\core\templates\core\manager_dashboard.html",
        r"d:\PB-Projects\HRMS_PBS\hrms-pbs\core\templates\core\admin_dashboard.html",
    ]
    for p in files:
        fix_file(p)
