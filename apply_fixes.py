#!/usr/bin/env python3
"""
Apply fixes to CryptoUniverse endpoints to resolve production errors.
"""

import os
import re
from pathlib import Path

def fix_admin_py():
    """Fix admin.py async database queries and Trade.amount references."""
    
    admin_file = Path("/c/Users/ASUS/CryptoUniverse/app/api/v1/endpoints/admin.py")
    
    print("📝 Fixing admin.py...")
    
    with open(admin_file, 'r') as f:
        content = f.read()
    
    # Fix 1: Replace Trade.amount with Trade.quantity
    content = content.replace('Trade.amount', 'Trade.quantity')
    print("  ✅ Fixed Trade.amount → Trade.quantity")
    
    # Fix 2: Fix db.query patterns to async
    # This is complex, so let's create specific replacements
    
    # Pattern 1: db.query(Model).filter(...).count()
    content = re.sub(
        r'(\s+)(\w+)\s*=\s*db\.query\((\w+)\)\.filter\((.*?)\)\.count\(\)',
        r'\1from sqlalchemy import select, func\n\1result = await db.execute(select(func.count(\3.id)).filter(\4))\n\1\2 = result.scalar()',
        content
    )
    
    # Pattern 2: db.query(Model).filter(...).first()
    content = re.sub(
        r'(\s+)(\w+)\s*=\s*db\.query\((\w+)\)\.filter\((.*?)\)\.first\(\)',
        r'\1from sqlalchemy import select\n\1result = await db.execute(select(\3).filter(\4))\n\1\2 = result.scalars().first()',
        content
    )
    
    # Pattern 3: query = db.query(Model)
    content = re.sub(
        r'(\s+)query\s*=\s*db\.query\((\w+)\)',
        r'\1from sqlalchemy import select\n\1stmt = select(\2)',
        content
    )
    
    # Save the fixed file
    with open(admin_file, 'w') as f:
        f.write(content)
    
    print("  ✅ Fixed async query patterns")

def fix_telegram_py():
    """Fix telegram.py self reference errors."""
    
    telegram_file = Path("/c/Users/ASUS/CryptoUniverse/app/api/v1/endpoints/telegram.py")
    
    print("📝 Fixing telegram.py...")
    
    with open(telegram_file, 'r') as f:
        content = f.read()
    
    # Remove self. references (these are in function-based endpoints, not class methods)
    content = re.sub(r'self\.(\w+)', r'\1', content)
    
    # Ensure proper service imports
    if 'from app.services.telegram_commander import telegram_commander' not in content:
        # Add import at the top after other imports
        import_section = """from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.telegram_commander import telegram_commander
"""
        content = content.replace(
            'from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks\nfrom sqlalchemy.ext.asyncio import AsyncSession',
            import_section
        )
    
    with open(telegram_file, 'w') as f:
        f.write(content)
    
    print("  ✅ Fixed self references")

def add_missing_market_endpoints():
    """Add missing market endpoints."""
    
    market_file = Path("/c/Users/ASUS/CryptoUniverse/app/api/v1/endpoints/market_analysis.py")
    
    print("📝 Adding missing market endpoints...")
    
    with open(market_file, 'r') as f:
        content = f.read()
    
    # Check if /prices endpoint exists
    if '@router.get("/prices")' not in content:
        # Add the prices endpoint
        prices_endpoint = '''

@router.get("/prices")
async def get_market_prices(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get current market prices for all tracked symbols."""
    try:
        from app.services.market_data_feeds import market_data_feeds
        from datetime import datetime
        
        # Get prices for major coins
        symbols = ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "MATIC"]
        prices = {}
        
        for symbol in symbols:
            price_data = await market_data_feeds.get_real_time_price(symbol)
            if price_data and price_data.get("success"):
                prices[symbol] = price_data
        
        return {
            "success": True,
            "prices": prices,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get market prices: {e}")
        raise HTTPException(status_code=500, detail=str(e))
'''
        content += prices_endpoint
        print("  ✅ Added /prices endpoint")
    
    with open(market_file, 'w') as f:
        f.write(content)

def main():
    """Run all fixes."""
    print("🚀 Applying CryptoUniverse fixes...\n")
    
    try:
        fix_admin_py()
        fix_telegram_py() 
        add_missing_market_endpoints()
        
        print("\n✅ All fixes applied successfully!")
        print("\n📋 Next steps:")
        print("1. Test locally: python main.py")
        print("2. Commit changes: git add -A && git commit -m 'Fix: Admin async queries, telegram self ref, add market prices'")
        print("3. Push to deploy: git push origin main")
        
    except Exception as e:
        print(f"\n❌ Error during fixes: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()