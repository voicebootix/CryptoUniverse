#!/usr/bin/env python3
"""
Fix async database queries in admin.py
"""

import re

# Read the file
with open('app/api/v1/endpoints/admin.py', 'r') as f:
    content = f.read()

# Fix list_users function (around line 458)
old_list_users = """        query = db.query(User)
        
        # Apply filters
        if status_filter:
            query = query.filter(User.status == status_filter)
        if role_filter:
            query = query.filter(User.role == role_filter)
        if search:
            query = query.filter(
                or_(
                    User.email.contains(search),
                    User.username.contains(search)
                )
            )
        
        # Sort
        query = query.order_by(User.created_at.desc())
        
        # Paginate
        total = query.count()
        users = query.offset(skip).limit(limit).all()
        
        # Count by status
        active_count = db.query(User).filter(User.status == UserStatus.ACTIVE).count()
        trading_count = db.query(User).filter("""

new_list_users = """        from sqlalchemy import select, or_
        
        # Build query
        stmt = select(User)
        
        # Apply filters
        if status_filter:
            stmt = stmt.filter(User.status == status_filter)
        if role_filter:
            stmt = stmt.filter(User.role == role_filter)
        if search:
            stmt = stmt.filter(
                or_(
                    User.email.contains(search),
                    User.username.contains(search)
                )
            )
        
        # Sort
        stmt = stmt.order_by(User.created_at.desc())
        
        # Get total count
        count_stmt = select(func.count()).select_from(User)
        if status_filter:
            count_stmt = count_stmt.filter(User.status == status_filter)
        if role_filter:
            count_stmt = count_stmt.filter(User.role == role_filter)
        if search:
            count_stmt = count_stmt.filter(
                or_(
                    User.email.contains(search),
                    User.username.contains(search)
                )
            )
        
        total_result = await db.execute(count_stmt)
        total = total_result.scalar()
        
        # Paginate
        stmt = stmt.offset(skip).limit(limit)
        result = await db.execute(stmt)
        users = result.scalars().all()
        
        # Count by status
        active_count_result = await db.execute(
            select(func.count()).select_from(User).filter(User.status == UserStatus.ACTIVE)
        )
        active_count = active_count_result.scalar()
        
        trading_count_result = await db.execute(
            select(func.count()).select_from(User).filter("""

content = content.replace(old_list_users, new_list_users)

# Fix other db.query patterns
# Pattern: credit_account = db.query(CreditAccount).filter(...).first()
content = re.sub(
    r'credit_account = db\.query\(CreditAccount\)\.filter\(\s*CreditAccount\.user_id == user\.id\s*\)\.first\(\)',
    '''credit_result = await db.execute(
                select(CreditAccount).filter(CreditAccount.user_id == user.id)
            )
            credit_account = credit_result.scalar_one_or_none()''',
    content
)

# Pattern: trade_count = db.query(Trade).filter(Trade.user_id == user.id).count()
content = re.sub(
    r'trade_count = db\.query\(Trade\)\.filter\(Trade\.user_id == user\.id\)\.count\(\)',
    '''trade_count_result = await db.execute(
                select(func.count()).select_from(Trade).filter(Trade.user_id == user.id)
            )
            trade_count = trade_count_result.scalar()''',
    content
)

# Fix manage_user function (line 555)
content = re.sub(
    r'target_user = db\.query\(User\)\.filter\(User\.id == request\.user_id\)\.first\(\)',
    '''user_result = await db.execute(
            select(User).filter(User.id == request.user_id)
        )
        target_user = user_result.scalar_one_or_none()''',
    content
)

# Fix get_metrics function (line 672-677)
old_metrics = """        active_users = db.query(User).filter(
            User.status == UserStatus.ACTIVE
        ).count()
        
        # Trading activity
        trades_today = db.query(Trade).filter("""

new_metrics = """        active_users_result = await db.execute(
            select(func.count()).select_from(User).filter(
                User.status == UserStatus.ACTIVE
            )
        )
        active_users = active_users_result.scalar()
        
        # Trading activity
        trades_today_result = await db.execute(
            select(func.count()).select_from(Trade).filter("""

content = content.replace(old_metrics, new_metrics)

# Fix volume_24h query (line 682)
old_volume = """        volume_24h = db.query(func.sum(Trade.quantity)).filter(
            Trade.created_at >= datetime.utcnow() - timedelta(hours=24)
        ).scalar() or 0"""

new_volume = """        volume_result = await db.execute(
            select(func.sum(Trade.quantity)).filter(
                Trade.created_at >= datetime.utcnow() - timedelta(hours=24)
            )
        )
        volume_24h = volume_result.scalar() or 0"""

content = content.replace(old_volume, new_volume)

# Fix audit log queries (line 741, 781)
content = re.sub(
    r'query = db\.query\(AuditLog\)',
    'stmt = select(AuditLog)',
    content
)

content = re.sub(
    r'user = db\.query\(User\)\.filter\(User\.id == log\.user_id\)\.first\(\)',
    '''user_result = await db.execute(
                select(User).filter(User.id == log.user_id)
            )
            user = user_result.scalar_one_or_none()''',
    content
)

# Write the fixed content back
with open('app/api/v1/endpoints/admin.py', 'w') as f:
    f.write(content)

print("✅ Fixed admin.py async queries")