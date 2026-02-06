#!/usr/bin/env python3
"""
Alternative fix: Remove simulation fields from User model.

This is a temporary fix that removes the simulation fields from the User model
to match the current database schema. Use this only if you cannot apply the
database migration immediately.
"""

import os
import shutil
from datetime import datetime

def remove_simulation_fields():
    """Remove simulation fields from the User model."""
    
    model_file = "/workspace/app/models/user.py"
    backup_file = f"/workspace/app/models/user.py.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Create backup
    shutil.copy2(model_file, backup_file)
    print(f"✅ Created backup: {backup_file}")
    
    # Read the file
    with open(model_file, 'r') as f:
        lines = f.readlines()
    
    # Find and comment out the simulation fields (lines 97-100)
    modified_lines = []
    skip_lines = False
    
    for i, line in enumerate(lines, 1):
        # Comment out lines 97-100 (simulation fields)
        if i >= 97 and i <= 100:
            if not line.strip().startswith('#'):
                modified_lines.append(f"    # TEMPORARILY DISABLED: {line[4:]}")
            else:
                modified_lines.append(line)
        else:
            modified_lines.append(line)
    
    # Write back the modified file
    with open(model_file, 'w') as f:
        f.writelines(modified_lines)
    
    print(f"✅ Modified {model_file}")
    print("⚠️  Note: This is a temporary fix. The proper solution is to apply the database migration.")
    print(f"    To restore, use: cp {backup_file} {model_file}")

if __name__ == "__main__":
    remove_simulation_fields()