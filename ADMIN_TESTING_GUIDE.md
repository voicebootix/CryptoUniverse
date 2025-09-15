
# ADMIN STRATEGY TESTING GUIDE

## IMMEDIATE TESTING (No Credits Required)

### Test Working Strategies:
```bash
# Test risk management
curl -X POST "https://cryptouniverse.onrender.com/api/v1/strategies/execute" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"function": "risk_management", "symbol": "BTC/USDT", "parameters": {}}'

# Test portfolio optimization  
curl -X POST "https://cryptouniverse.onrender.com/api/v1/strategies/execute" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"function": "portfolio_optimization", "symbol": "BTC/USDT", "parameters": {}}'

# Test algorithmic trading
curl -X POST "https://cryptouniverse.onrender.com/api/v1/strategies/execute" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"function": "algorithmic_trading", "symbol": "BTC/USDT", "parameters": {"strategy_type": "momentum"}}'
```

## AFTER PRODUCTION RESTART

### Test New Admin Endpoints:
```bash
# Test any strategy without purchase
curl -X POST "https://cryptouniverse.onrender.com/api/v1/admin/testing/strategy/execute" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"function": "funding_arbitrage", "symbol": "BTC/USDT", "parameters": {}}'

# List all available functions
curl -X GET "https://cryptouniverse.onrender.com/api/v1/admin/testing/strategy/list-all" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Bulk test multiple strategies
curl -X POST "https://cryptouniverse.onrender.com/api/v1/admin/testing/strategy/bulk-test" \
  -H "Authorization: Bearer YOUR_TOKEN" \
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
