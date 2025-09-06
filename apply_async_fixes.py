#!/usr/bin/env python3
"""Apply async fixes to admin.py"""

import re

# Read the file
with open('app/api/v1/endpoints/admin.py', 'r') as f:
    lines = f.readlines()

# Fix 1: Import necessary functions at the top
import_added = False
for i, line in enumerate(lines):
    if 'from sqlalchemy import' in line and not import_added:
        if 'select' not in line:
            lines[i] = line.rstrip() + ', select\n'
        if 'func' not in line:
            lines[i] = lines[i].rstrip() + ', func\n'
        if 'or_' not in line:
            lines[i] = lines[i].rstrip() + ', or_\n'
        if 'and_' not in line:
            lines[i] = lines[i].rstrip() + ', and_\n'
        import_added = True
        break

if not import_added:
    # Add import at the beginning of imports section
    for i, line in enumerate(lines):
        if line.startswith('from sqlalchemy'):
            lines.insert(i+1, 'from sqlalchemy import select, func, or_, and_\n')
            break

# Fix 2: Fix the list_users function (around line 458)
for i in range(len(lines)):
    if 'query = db.query(User)' in lines[i]:
        # Replace the sync query pattern with async
        lines[i] = '        # Build query using async pattern\n'
        lines.insert(i+1, '        stmt = select(User)\n')
        lines.insert(i+2, '        count_stmt = select(func.count()).select_from(User)\n')
        break

# Fix 3: Replace query.filter with stmt.filter
for i in range(len(lines)):
    if 'query = query.filter' in lines[i]:
        lines[i] = lines[i].replace('query = query.filter', 'stmt = stmt.filter')
        # Also update count_stmt
        if 'status_filter' in lines[i]:
            lines.insert(i+1, '            count_stmt = count_stmt.filter(User.status == status_filter)\n')
        elif 'role_filter' in lines[i]:
            lines.insert(i+1, '            count_stmt = count_stmt.filter(User.role == role_filter)\n')

# Fix 4: Fix query.count()
for i in range(len(lines)):
    if 'total_count = query.count()' in lines[i]:
        lines[i] = '        # Get total count with async\n'
        lines.insert(i+1, '        total_result = await db.execute(count_stmt)\n')
        lines.insert(i+2, '        total_count = total_result.scalar()\n')
        break

# Fix 5: Fix query.offset().limit().all()
for i in range(len(lines)):
    if 'users = query.offset(skip).limit(limit).all()' in lines[i]:
        lines[i] = '        # Get paginated results with async\n'
        lines.insert(i+1, '        stmt = stmt.offset(skip).limit(limit)\n')
        lines.insert(i+2, '        result = await db.execute(stmt)\n')
        lines.insert(i+3, '        users = result.scalars().all()\n')
        break

# Fix 6: Fix active_count
for i in range(len(lines)):
    if 'active_count = db.query(User).filter(User.status == UserStatus.ACTIVE).count()' in lines[i]:
        lines[i] = '        # Count active users with async\n'
        lines.insert(i+1, '        active_count_result = await db.execute(\n')
        lines.insert(i+2, '            select(func.count()).select_from(User).filter(User.status == UserStatus.ACTIVE)\n')
        lines.insert(i+3, '        )\n')
        lines.insert(i+4, '        active_count = active_count_result.scalar()\n')
        break

# Fix 7: Fix trading_count (multi-line)
for i in range(len(lines)):
    if 'trading_count = db.query(User).filter(' in lines[i]:
        # Find the end of this statement (look for ).count())
        end_idx = i
        for j in range(i, min(i+10, len(lines))):
            if ').count()' in lines[j]:
                end_idx = j
                break
        
        # Replace the whole block
        lines[i] = '        # Count trading users with async\n'
        lines[i+1] = '        trading_count_result = await db.execute(\n'
        lines[i+2] = '            select(func.count()).select_from(User).filter(\n'
        # Keep the filter conditions
        for j in range(i+3, end_idx):
            lines[j] = '            ' + lines[j].strip() + '\n'
        lines[end_idx] = '            )\n'
        lines.insert(end_idx+1, '        )\n')
        lines.insert(end_idx+2, '        trading_count = trading_count_result.scalar()\n')
        break

# Fix 8: Fix other db.query patterns
for i in range(len(lines)):
    # Fix credit_account query
    if 'credit_account = db.query(CreditAccount).filter(' in lines[i]:
        if 'CreditAccount.user_id == user.id' in lines[i]:
            lines[i] = '            # Get credit account with async\n'
            lines.insert(i+1, '            credit_result = await db.execute(\n')
            lines.insert(i+2, '                select(CreditAccount).filter(CreditAccount.user_id == user.id)\n')
            lines.insert(i+3, '            )\n')
            lines.insert(i+4, '            credit_account = credit_result.scalar_one_or_none()\n')
    
    # Fix trade_count query
    if 'trade_count = db.query(Trade).filter(Trade.user_id == user.id).count()' in lines[i]:
        lines[i] = '            # Count trades with async\n'
        lines.insert(i+1, '            trade_count_result = await db.execute(\n')
        lines.insert(i+2, '                select(func.count()).select_from(Trade).filter(Trade.user_id == user.id)\n')
        lines.insert(i+3, '            )\n')
        lines.insert(i+4, '            trade_count = trade_count_result.scalar()\n')

# Fix 9: Fix target_user query (line ~555)
for i in range(len(lines)):
    if 'target_user = db.query(User).filter(User.id == request.user_id).first()' in lines[i]:
        lines[i] = '        # Get target user with async\n'
        lines.insert(i+1, '        user_result = await db.execute(\n')
        lines.insert(i+2, '            select(User).filter(User.id == request.user_id)\n')
        lines.insert(i+3, '        )\n')
        lines.insert(i+4, '        target_user = user_result.scalar_one_or_none()\n')
        break

# Fix 10: Fix active_users in get_detailed_metrics (line ~672)
for i in range(len(lines)):
    if 'active_users = db.query(User).filter(' in lines[i] and 'UserStatus.ACTIVE' in lines[i+1]:
        lines[i] = '        # Count active users with async\n'
        lines[i+1] = '        active_users_result = await db.execute(\n'
        lines.insert(i+2, '            select(func.count()).select_from(User).filter(\n')
        lines.insert(i+3, '                User.status == UserStatus.ACTIVE\n')
        lines.insert(i+4, '            )\n')
        lines.insert(i+5, '        )\n')
        lines.insert(i+6, '        active_users = active_users_result.scalar()\n')
        break

# Fix 11: Fix trades_today query (line ~677)
for i in range(len(lines)):
    if 'trades_today = db.query(Trade).filter(' in lines[i]:
        lines[i] = '        # Count today\'s trades with async\n'
        lines.insert(i+1, '        trades_today_result = await db.execute(\n')
        lines.insert(i+2, '            select(func.count()).select_from(Trade).filter(\n')
        # The filter condition continues on next line, handle it
        break

# Fix 12: Fix volume_24h query (already has Trade.quantity from previous fix)
for i in range(len(lines)):
    if 'volume_24h = db.query(func.sum(Trade.quantity)).filter(' in lines[i]:
        lines[i] = '        # Calculate 24h volume with async\n'
        lines.insert(i+1, '        volume_result = await db.execute(\n')
        lines.insert(i+2, '            select(func.sum(Trade.quantity)).filter(\n')
        # Handle the filter condition on next line
        for j in range(i+3, min(i+10, len(lines))):
            if ').scalar() or 0' in lines[j]:
                lines[j] = '            )\n'
                lines.insert(j+1, '        )\n')
                lines.insert(j+2, '        volume_24h = volume_result.scalar() or 0\n')
                break
        break

# Write the fixed content back
with open('app/api/v1/endpoints/admin.py', 'w') as f:
    f.writelines(lines)

print("✅ Async fixes applied to admin.py")