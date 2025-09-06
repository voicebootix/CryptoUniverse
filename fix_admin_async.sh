#!/bin/bash

echo "Fixing async queries in admin.py..."

# Create a backup first
cp app/api/v1/endpoints/admin.py app/api/v1/endpoints/admin.py.backup

# Fix 1: Replace db.query(User) pattern at line 458
sed -i '458s/query = db.query(User)/from sqlalchemy import select, func, or_, and_\n        stmt = select(User)/' app/api/v1/endpoints/admin.py

# Fix 2: Replace query.filter with stmt.filter
sed -i 's/query = query\.filter/stmt = stmt.filter/g' app/api/v1/endpoints/admin.py

# Fix 3: Replace query.count() with async pattern
sed -i 's/total_count = query\.count()/total_result = await db.execute(select(func.count()).select_from(User))\n        total_count = total_result.scalar()/' app/api/v1/endpoints/admin.py

# Fix 4: Replace query.offset().limit().all() with async pattern
sed -i 's/users = query\.offset(skip)\.limit(limit)\.all()/stmt = stmt.offset(skip).limit(limit)\n        result = await db.execute(stmt)\n        users = result.scalars().all()/' app/api/v1/endpoints/admin.py

# Fix 5: Fix active_count query
sed -i 's/active_count = db\.query(User)\.filter(User\.status == UserStatus\.ACTIVE)\.count()/active_count_result = await db.execute(select(func.count()).select_from(User).filter(User.status == UserStatus.ACTIVE))\n        active_count = active_count_result.scalar()/' app/api/v1/endpoints/admin.py

# Fix 6: Fix trading_count - this is multi-line, needs special handling
perl -i -pe 's/trading_count = db\.query\(User\)\.filter\(/trading_count_result = await db.execute(select(func.count()).select_from(User).filter(/g' app/api/v1/endpoints/admin.py
perl -i -pe 's/\)\.count\(\)/)) if $. == 486; $_ .= "        trading_count = trading_count_result.scalar()\n" if $. == 486/' app/api/v1/endpoints/admin.py

echo "✅ Basic async patterns fixed"
echo ""
echo "Note: Manual review recommended for complex queries"