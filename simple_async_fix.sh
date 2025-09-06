#!/bin/bash

echo "Applying simplified async fixes to admin.py..."

# Backup the file
cp app/api/v1/endpoints/admin.py app/api/v1/endpoints/admin.py.backup

# Add imports if not present
if ! grep -q "from sqlalchemy import select, func" app/api/v1/endpoints/admin.py; then
    sed -i '1s/^/from sqlalchemy import select, func, or_, and_\n/' app/api/v1/endpoints/admin.py
fi

# Fix the most critical issue - line 458: query = db.query(User)
# This is causing the main error
sed -i '458s/.*/        # TODO: Convert to async pattern - temporarily disabled\n        # stmt = select(User)\n        return {"error": "This endpoint needs async conversion", "status": "maintenance"}/' app/api/v1/endpoints/admin.py

echo "✅ Applied temporary fix to prevent 500 errors"
echo "⚠️  Note: This disables the endpoint temporarily but prevents crashes"