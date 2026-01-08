
import os

file_path = 'core/templates/core/base.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Define the broken string pattern (handling varying whitespace)
# The broken part looks like:
# ... year{% if years_service > 1
#                         %}s{% endif %} ...

# We will try to match this specific sequence
search_str = 'year{% if years_service > 1'
if search_str in content:
    print("Found the start of the broken tag.")
    
    # Simple replace logic - find the split sequence and join it
    # We might need to handle the newline and indentation generically
    import re
    
    # Regex to match:
    # year{% if years_service > 1
    # [whitespace] %}s{% endif %}
    
    pattern = r'(year\{\% if years_service > 1)\s+(\%\}\s*s\{\% endif \%\})'
    
    # We want to replace it with:
    # year{% if years_service > 1 %}s{% endif %}
    
    new_content = re.sub(pattern, r'\1 \2', content)
    
    # Also clean up the spaces/newlines inside the join
    # The regex above just changes newline to space, but let's be more precise
    
    # Better approach: precise string search and replace including newline
    # Scan for the newline version manually if regex is tricky
    
    custom_broken = """year{% if years_service > 1
                        %}s{% endif %}"""
    
    if custom_broken in content:
        print("Found exact broken match with assumed indentation.")
        content = content.replace(custom_broken, "year{% if years_service > 1 %}s{% endif %}")
    else:
        # Fallback to regex if exact string mismatch (e.g. different spaces)
        print("Exact string not found, trying regex...")
        content = re.sub(r'year\{\%\s*if\s*years_service\s*>\s*1\s*(\r\n|\n|\r)\s*\%\}\s*s\{\%\s*endif\s*\%\}', 
                         r'year{% if years_service > 1 %}s{% endif %}', 
                         content)
                         
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed file.")

else:
    print("Could not find the broken tag start string.")
