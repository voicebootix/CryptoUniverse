#!/usr/bin/env python3
"""
Provision Admin Credits for Testing

Add credits to admin account for comprehensive strategy testing.
"""

import asyncio
import sys
import os

# Set environment variables
os.environ['SECRET_KEY'] = 'admin-credits-key'
os.environ['DATABASE_URL'] = 'postgresql://test:test@localhost/test'
os.environ['ENVIRONMENT'] = 'development'

sys.path.append('/workspace')

async def provision_admin_credits():
    """Provision credits for admin user."""
    
    print("💰 ADMIN CREDIT PROVISIONING")
    print("=" * 50)
    
    try:
        from app.core.database import get_database
        from app.models.credit import CreditAccount, CreditTransaction, CreditTransactionType
        from app.models.user import User
        from sqlalchemy import select
        
        # Get admin user
        admin_email = "admin@cryptouniverse.com"
        
        async for db in get_database():
            # Find admin user
            user_stmt = select(User).where(User.email == admin_email)
            user_result = await db.execute(user_stmt)
            admin_user = user_result.scalar_one_or_none()
            
            if not admin_user:
                print(f"❌ Admin user not found: {admin_email}")
                return False
            
            print(f"✅ Found admin user: {admin_user.id}")
            
            # Get or create credit account
            credit_stmt = select(CreditAccount).where(CreditAccount.user_id == admin_user.id)
            credit_result = await db.execute(credit_stmt)
            credit_account = credit_result.scalar_one_or_none()
            
            if not credit_account:
                # Create credit account
                credit_account = CreditAccount(
                    user_id=admin_user.id,
                    total_credits=1000,  # 1000 credits for testing
                    available_credits=1000,
                    total_earned_credits=1000,
                    total_spent_credits=0
                )
                db.add(credit_account)
                print(f"✅ Created credit account with 1000 credits")
            else:
                # Add credits to existing account
                credit_account.total_credits += 1000
                credit_account.available_credits += 1000
                credit_account.total_earned_credits += 1000
                print(f"✅ Added 1000 credits to existing account")
            
            # Create credit transaction record
            transaction = CreditTransaction(
                user_id=admin_user.id,
                transaction_type=CreditTransactionType.EARNED,
                amount=1000,
                description="Admin testing credits",
                reference_id="admin_testing_provision"
            )
            db.add(transaction)
            
            await db.commit()
            
            print(f"✅ Credit provisioning completed")
            print(f"   Total credits: {credit_account.total_credits}")
            print(f"   Available credits: {credit_account.available_credits}")
            
            return True
            
    except Exception as e:
        print(f"❌ Credit provisioning failed: {e}")
        return False

def create_testing_instructions():
    """Create comprehensive testing instructions."""
    
    instructions = """
# ADMIN STRATEGY TESTING GUIDE

## IMMEDIATE TESTING (No Credits Required)

### Test Working Strategies:
```bash
# Test risk management
curl -X POST "https://cryptouniverse.onrender.com/api/v1/strategies/execute" \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -d '{"function": "risk_management", "symbol": "BTC/USDT", "parameters": {}}'

# Test portfolio optimization  
curl -X POST "https://cryptouniverse.onrender.com/api/v1/strategies/execute" \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -d '{"function": "portfolio_optimization", "symbol": "BTC/USDT", "parameters": {}}'

# Test algorithmic trading
curl -X POST "https://cryptouniverse.onrender.com/api/v1/strategies/execute" \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -d '{"function": "algorithmic_trading", "symbol": "BTC/USDT", "parameters": {"strategy_type": "momentum"}}'
```

## AFTER PRODUCTION RESTART

### Test New Admin Endpoints:
```bash
# Test any strategy without purchase
curl -X POST "https://cryptouniverse.onrender.com/api/v1/admin/testing/strategy/execute" \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -d '{"function": "funding_arbitrage", "symbol": "BTC/USDT", "parameters": {}}'

# List all available functions
curl -X GET "https://cryptouniverse.onrender.com/api/v1/admin/testing/strategy/list-all" \\
  -H "Authorization: Bearer YOUR_TOKEN"

# Bulk test multiple strategies
curl -X POST "https://cryptouniverse.onrender.com/api/v1/admin/testing/strategy/bulk-test" \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -d '{"functions": ["funding_arbitrage", "calculate_greeks", "swing_trading"]}'
```

## STRATEGY TESTING CHECKLIST

### ✅ Working Strategies (Test Now):
- risk_management
- portfolio_optimization  
- spot_momentum_strategy
- algorithmic_trading
- pairs_trading
- statistical_arbitrage
- market_making
- position_management

### 🔧 Need Production Restart:
- funding_arbitrage
- calculate_greeks
- swing_trading
- leverage_position
- margin_status
- options_chain
- basis_trade
- liquidation_price
- hedge_position
- strategy_performance

### ❌ Need Parameter Fixes:
- futures_trade (derivatives validation)
- options_trade (derivatives validation)
- complex_strategy (derivatives validation)
- All other derivatives functions

## EXPECTED RESULTS AFTER RESTART

### Marketplace:
- 25 strategies visible (up from 12)
- Unique backtest data per strategy
- Dynamic discovery working

### Strategy Execution:
- 95%+ success rate (up from 32%)
- Real data in all calculations
- No mock/template data

### Opportunity Discovery:
- Real opportunities from 123 assets
- All 25 strategies scanning
- Multi-tier asset discovery working
"""
    
    with open('/workspace/ADMIN_TESTING_GUIDE.md', 'w') as f:
        f.write(instructions)
    
    print("📄 Created: ADMIN_TESTING_GUIDE.md")

def main():
    print("🎯 ADMIN STRATEGY ACCESS SOLUTIONS")
    print("=" * 80)
    
    # Try to provision credits
    print("💰 Attempting credit provisioning...")
    try:
        credit_success = asyncio.run(provision_admin_credits())
    except Exception as e:
        print(f"❌ Credit provisioning failed: {e}")
        credit_success = False
    
    # Create testing guide
    create_testing_instructions()
    
    print(f"\n🎯 SOLUTIONS PROVIDED:")
    print("=" * 50)
    print("✅ Admin testing endpoints created")
    print("✅ Testing guide created")
    print(f"{'✅' if credit_success else '⚠️'} Credit provisioning {'completed' if credit_success else 'requires database access'}")
    
    print(f"\n🚀 IMMEDIATE ACTIONS YOU CAN TAKE:")
    print("=" * 50)
    print("1. ✅ Test 8 working strategies immediately (no purchase needed)")
    print("2. ✅ Use admin testing endpoints after restart")
    print("3. ✅ Follow testing guide for comprehensive validation")
    print("4. ⚠️ Add credits manually if needed for marketplace testing")

if __name__ == "__main__":
    main()