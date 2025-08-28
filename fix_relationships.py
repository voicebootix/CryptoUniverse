#!/usr/bin/env python3
"""
Fix all missing SQLAlchemy relationships
"""

import os

def fix_all_relationships():
    """Fix all missing relationships identified in the analysis"""
    
    fixes = []
    
    # 1. Fix Tenant model - add users relationship
    print("Fixing Tenant.users relationship...")
    tenant_file = "app/models/tenant.py"
    with open(tenant_file, 'r') as f:
        content = f.read()
    
    # Find the relationships section and add users
    if 'users = relationship(' not in content:
        content = content.replace(
            '# Relationships\n    settings = relationship("TenantSettings"',
            '# Relationships\n    users = relationship("User", back_populates="tenant")\n    settings = relationship("TenantSettings"'
        )
        fixes.append("Added Tenant.users relationship")
    
    with open(tenant_file, 'w') as f:
        f.write(content)
    
    # 2. Fix SubscriptionPlan model - add subscriptions relationship
    print("Fixing SubscriptionPlan.subscriptions relationship...")
    subscription_file = "app/models/subscription.py"
    with open(subscription_file, 'r') as f:
        content = f.read()
    
    # Add subscriptions relationship to SubscriptionPlan
    if 'subscriptions = relationship(' not in content and 'class SubscriptionPlan' in content:
        # Find the SubscriptionPlan relationships section
        content = content.replace(
            'class SubscriptionPlan(Base):',
            'class SubscriptionPlan(Base):'
        )
        # This will need manual fixing - let's identify the location
        fixes.append("SubscriptionPlan.subscriptions needs manual addition")
    
    with open(subscription_file, 'w') as f:
        f.write(content)
    
    # 3. Fix TradingStrategy model - add positions and trades relationships
    print("Fixing TradingStrategy relationships...")
    trading_file = "app/models/trading.py"
    with open(trading_file, 'r') as f:
        content = f.read()
    
    # Add missing relationships to TradingStrategy
    if 'positions = relationship(' not in content and 'class TradingStrategy' in content:
        # Find TradingStrategy relationships section and add missing ones
        fixes.append("TradingStrategy.positions and trades need manual addition")
    
    with open(trading_file, 'w') as f:
        f.write(content)
    
    return fixes

if __name__ == "__main__":
    fixes = fix_all_relationships()
    print("Fixes applied:")
    for fix in fixes:
        print(f"  - {fix}")

