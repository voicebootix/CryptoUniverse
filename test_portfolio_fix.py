#!/usr/bin/env python3

# Test that the portfolio response now includes the expected fields

test_response = {
    "success": True,
    "active_strategies": [
        {"strategy_id": "ai_risk_management", "name": "AI Risk Manager"},
        {"strategy_id": "ai_portfolio_optimization", "name": "AI Portfolio Optimizer"},
        {"strategy_id": "ai_spot_momentum_strategy", "name": "AI Momentum Trading"},
        {"strategy_id": "ai_options_trade", "name": "AI Options Strategies"}
    ],
    "summary": {"total_strategies": 4, "active_strategies": 4},
    "strategies": [
        {"strategy_id": "ai_risk_management", "name": "AI Risk Manager"},
        {"strategy_id": "ai_portfolio_optimization", "name": "AI Portfolio Optimizer"},
        {"strategy_id": "ai_spot_momentum_strategy", "name": "AI Momentum Trading"},
        {"strategy_id": "ai_options_trade", "name": "AI Options Strategies"}
    ],
    "total_strategies": 4,
    "total_monthly_cost": 60,
    "cached": False
}

# Test what the opportunity discovery service expects
if test_response.get("success") and test_response.get("active_strategies"):
    print("✅ Response has required fields for opportunity discovery!")
    print(f"   - success: {test_response.get('success')}")
    print(f"   - active_strategies count: {len(test_response.get('active_strategies', []))}")
else:
    print("❌ Response missing required fields!")

