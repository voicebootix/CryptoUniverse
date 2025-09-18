#!/usr/bin/env python3
"""
Fix all nullable numeric fields in user_opportunity_discovery.py
"""

import re

def fix_nullable_fields():
    file_path = '/workspace/app/services/user_opportunity_discovery.py'
    
    # Read the file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Track changes
    changes = []
    
    # Pattern 1: float(dict.get("key", default)) where dict.get() might return None
    # This pattern is vulnerable because dict.get("key", default) returns None if key exists with None value
    pattern1 = r'float\((\w+)\.get\("([^"]+)", ([^)]+)\)\)'
    
    def fix_pattern1(match):
        var_name = match.group(1)
        key = match.group(2)
        default = match.group(3)
        original = match.group(0)
        fixed = f'float({var_name}.get("{key}") or {default})'
        changes.append(f"Fixed: {original} -> {fixed}")
        return fixed
    
    # Apply fix for pattern 1
    content = re.sub(pattern1, fix_pattern1, content)
    
    # Pattern 2: float(dict.get("key")) without default - these need a default added
    pattern2 = r'float\((\w+)\.get\("([^"]+)"\)\)'
    
    def fix_pattern2(match):
        var_name = match.group(1)
        key = match.group(2)
        original = match.group(0)
        # Determine appropriate default based on key name
        if 'profit' in key or 'capital' in key or 'amount' in key:
            default = '0'
        elif 'confidence' in key or 'score' in key:
            default = '0.5'
        else:
            default = '0'
        fixed = f'float({var_name}.get("{key}") or {default})'
        changes.append(f"Fixed: {original} -> {fixed}")
        return fixed
    
    # Apply fix for pattern 2
    content = re.sub(pattern2, fix_pattern2, content)
    
    # Pattern 3: Special case for nested gets like indicators.get("price", {}).get("current", 0)
    # These are actually safe because they use {} as intermediate default, but let's make them more robust
    pattern3 = r'float\((\w+)\.get\("([^"]+)", \{\}\)\.get\("([^"]+)", ([^)]+)\)\)'
    
    def fix_pattern3(match):
        var_name = match.group(1)
        key1 = match.group(2)
        key2 = match.group(3)
        default = match.group(4)
        original = match.group(0)
        fixed = f'float(({var_name}.get("{key1}") or {{}}).get("{key2}") or {default})'
        changes.append(f"Fixed nested: {original} -> {fixed}")
        return fixed
    
    # Apply fix for pattern 3
    content = re.sub(pattern3, fix_pattern3, content)
    
    # Write the fixed content
    with open(file_path, 'w') as f:
        f.write(content)
    
    return changes

if __name__ == "__main__":
    print("Fixing all nullable numeric fields in user_opportunity_discovery.py...")
    changes = fix_nullable_fields()
    
    if changes:
        print(f"\nMade {len(changes)} fixes:")
        for change in changes:
            print(f"  - {change}")
    else:
        print("\nNo changes needed - all float conversions are already safe!")
    
    print("\nDone!")