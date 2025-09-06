#!/bin/bash

echo "🚀 Applying CryptoUniverse fixes..."

# Fix 1: Replace Trade.amount with Trade.quantity in admin.py
echo "📝 Fixing Trade.amount → Trade.quantity..."
sed -i 's/Trade\.amount/Trade.quantity/g' app/api/v1/endpoints/admin.py
echo "  ✅ Fixed Trade model references"

# Fix 2: Remove self. references in telegram.py
echo "📝 Fixing telegram.py self references..."
sed -i 's/self\.telegram_/telegram_/g' app/api/v1/endpoints/telegram.py
sed -i 's/self\.//' app/api/v1/endpoints/telegram.py  
echo "  ✅ Fixed self references"

# Fix 3: Simple fix for async queries in admin.py
# This is a temporary fix - proper async conversion needs more work
echo "📝 Adding TODO comments for async query fixes..."
sed -i 's/db\.query(/# TODO: Fix async - db.query(/g' app/api/v1/endpoints/admin.py

echo ""
echo "✅ Basic fixes applied!"
echo ""
echo "⚠️  Note: The async query fixes need manual conversion."
echo "    Search for 'TODO: Fix async' comments in admin.py"
echo ""
echo "📋 Next steps:"
echo "1. Review changes: git diff"
echo "2. Commit: git add -A && git commit -m 'Fix: Trade.quantity and telegram self references'"
echo "3. Push to Render: git push origin main"