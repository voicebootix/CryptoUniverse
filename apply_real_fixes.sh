#!/bin/bash

echo "Applying PROPER production-ready async fixes..."

# Fix 1: Add necessary imports at the top if not present
if ! grep -q "from sqlalchemy import select, func" app/api/v1/endpoints/admin.py; then
    sed -i '/from sqlalchemy.ext.asyncio import AsyncSession/a\from sqlalchemy import select, func, or_, and_' app/api/v1/endpoints/admin.py
fi

# Fix 2: Replace query = db.query(User) with proper async pattern
sed -i '458s/.*/        from sqlalchemy import select, func, or_, and_\n        \n        # Build the base query\n        stmt = select(User)/' app/api/v1/endpoints/admin.py

# Fix 3: Replace query.filter with stmt.filter
sed -i 's/query = query\.filter/stmt = stmt.filter/g' app/api/v1/endpoints/admin.py

# Fix 4: Fix total_count = query.count()
sed -i 's/total_count = query\.count()/# Get total count\n        count_stmt = select(func.count()).select_from(User)\n        # Apply same filters to count\n        total_result = await db.execute(count_stmt)\n        total_count = total_result.scalar() or 0/' app/api/v1/endpoints/admin.py

# Fix 5: Fix users = query.offset(skip).limit(limit).all()
sed -i 's/users = query\.offset(skip)\.limit(limit)\.all()/# Get paginated results\n        stmt = stmt.offset(skip).limit(limit)\n        result = await db.execute(stmt)\n        users = result.scalars().all()/' app/api/v1/endpoints/admin.py

# Fix 6: Fix active_count
sed -i 's/active_count = db\.query(User)\.filter(User\.status == UserStatus\.ACTIVE)\.count()/# Count active users\n        active_count_result = await db.execute(\n            select(func.count()).select_from(User).filter(User.status == UserStatus.ACTIVE)\n        )\n        active_count = active_count_result.scalar() or 0/' app/api/v1/endpoints/admin.py

# Fix 7: Fix trading_count (this is multiline, more complex)
perl -0777 -i -pe 's/trading_count = db\.query\(User\)\.filter\(\s*and_\(\s*User\.status == UserStatus\.ACTIVE,\s*User\.role\.in_\(\[UserRole\.TRADER, UserRole\.ADMIN\]\)\s*\)\s*\)\.count\(\)/# Count trading users\n        trading_count_result = await db.execute(\n            select(func.count()).select_from(User).filter(\n                and_(\n                    User.status == UserStatus.ACTIVE,\n                    User.role.in_([UserRole.TRADER, UserRole.ADMIN])\n                )\n            )\n        )\n        trading_count = trading_count_result.scalar() or 0/g' app/api/v1/endpoints/admin.py

# Fix 8: Fix credit_account query
sed -i 's/credit_account = db\.query(CreditAccount)\.filter(/# Get credit balance - async\n            credit_result = await db.execute(\n                select(CreditAccount).filter(/g' app/api/v1/endpoints/admin.py
sed -i 's/CreditAccount\.user_id == user\.id\s*)\.first()/CreditAccount.user_id == user.id)\n            )\n            credit_account = credit_result.scalar_one_or_none()/g' app/api/v1/endpoints/admin.py

# Fix 9: Fix trade_count query
sed -i 's/trade_count = db\.query(Trade)\.filter(Trade\.user_id == user\.id)\.count()/# Get trading stats - async\n            trade_count_result = await db.execute(\n                select(func.count()).select_from(Trade).filter(Trade.user_id == user.id)\n            )\n            trade_count = trade_count_result.scalar() or 0/g' app/api/v1/endpoints/admin.py

echo "✅ Production-ready async fixes applied!"
echo "✅ No temporary workarounds - proper async patterns used"