#!/usr/bin/env python3
"""
Check all SQLAlchemy relationships for missing back_populates
"""

import re
import os
from collections import defaultdict

def check_all_relationships():
    models_dir = 'app/models'
    back_populates = defaultdict(list)
    
    # Find all back_populates references
    for root, dirs, files in os.walk(models_dir):
        for file in files:
            if file.endswith('.py') and file != '__init__.py':
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Find back_populates patterns
                    relationship_matches = re.findall(r'relationship\([^)]*back_populates=["\']([^"\']+)["\']', content)
                    
                    for back_pop in relationship_matches:
                        back_populates[back_pop].append(file)
                        
                except Exception as e:
                    print(f"Error reading {file}: {e}")
    
    print('=== RELATIONSHIP ANALYSIS ===\n')
    
    # Check for missing relationships
    missing_relationships = []
    
    for relationship_name, files in back_populates.items():
        if len(files) == 1:
            print(f'❌ MISSING: "{relationship_name}" only referenced in {files[0]}')
            missing_relationships.append((relationship_name, files[0]))
        else:
            print(f'✅ OK: "{relationship_name}" referenced in {files}')
    
    print(f'\n=== SUMMARY ===')
    if missing_relationships:
        print(f'Found {len(missing_relationships)} missing relationships:')
        for rel, file in missing_relationships:
            print(f'  - "{rel}" (only in {file})')
    else:
        print('All relationships appear to be properly configured!')
    
    return missing_relationships

if __name__ == "__main__":
    check_all_relationships()

