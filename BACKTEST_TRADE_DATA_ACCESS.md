# Accessing Detailed Backtest Trade Data

## Overview

The enhanced backtesting engine now captures complete trade information including:
- **Entry and Exit** prices and timestamps
- **Position Type** (LONG/SHORT)
- **Stop Loss** and **Take Profit** levels
- **Exit Reason** (TAKE_PROFIT, STOP_LOSS, MANUAL, BACKTEST_END)
- **PnL** and **Outcome** (WIN/LOSS/BREAKEVEN)

## Data Structure

Each trade in `closed_trades` array contains:

```json
{
  "trade_id": "BTC/USDT_2024-01-15T10:30:00_2024-01-16T14:20:00",
  "symbol": "BTC/USDT",
  "position_type": "LONG",  // or "SHORT"
  "entry_time": "2024-01-15T10:30:00",
  "exit_time": "2024-01-16T14:20:00",
  "entry_price": 45000.0,
  "exit_price": 46500.0,
  "quantity": 0.1,
  "stop_loss": 44000.0,  // or null if not set
  "take_profit": 47000.0,  // or null if not set
  "exit_reason": "TAKE_PROFIT",  // TAKE_PROFIT, STOP_LOSS, MANUAL, BACKTEST_END
  "pnl": 150.0,
  "pnl_pct": 3.33,
  "fees": 0.465,
  "cost_basis": 4500.0,
  "outcome": "WIN"  // WIN, LOSS, or BREAKEVEN
}
```

## API Endpoints

### 1. Get All Backtest Results (Summary)

**Endpoint:** `GET /api/v1/strategies/backtest-results`

**Query Parameters:**
- `strategy_id` (optional): Filter by strategy ID
- `limit` (default: 10): Number of results (1-100)
- `skip` (default: 0): Pagination offset

**Response:**
```json
{
  "success": true,
  "count": 5,
  "results": [
    {
      "id": "uuid-here",
      "strategy_id": "momentum_strategy",
      "strategy_name": "Momentum Trading",
      "start_date": "2024-01-01T00:00:00",
      "end_date": "2024-04-01T00:00:00",
      "total_trades": 42,
      "win_rate": 65.5,
      "total_return_pct": 12.5,
      "profit_factor": 1.85,
      "sharpe_ratio": 1.2,
      "max_drawdown": 8.5,
      "created_at": "2024-04-01T12:00:00"
    }
  ]
}
```

### 2. Get Detailed Backtest Result with All Trades

**Endpoint:** `GET /api/v1/strategies/backtest-results/{backtest_id}`

**Path Parameters:**
- `backtest_id`: UUID or strategy_id

**Query Parameters:**
- `include_trades` (default: true): Include detailed trade records

**Response:**
```json
{
  "success": true,
  "backtest_id": "uuid-here",
  "strategy_id": "momentum_strategy",
  "strategy_name": "Momentum Trading",
  "start_date": "2024-01-01T00:00:00",
  "end_date": "2024-04-01T00:00:00",
  "period_days": 90,
  "initial_capital": 10000.0,
  "final_capital": 11250.0,
  "total_return": 1250.0,
  "total_return_pct": 12.5,
  "total_trades": 42,
  "winning_trades": 28,
  "losing_trades": 14,
  "win_rate": 66.67,
  "profit_factor": 1.85,
  "sharpe_ratio": 1.2,
  "max_drawdown": 8.5,
  "symbols": ["BTC/USDT", "ETH/USDT"],
  "data_source": "real_market_data",
  "created_at": "2024-04-01T12:00:00",
  "total_trades_detailed": 42,
  "trades": [
    {
      "trade_id": "BTC/USDT_2024-01-15T10:30:00_2024-01-16T14:20:00",
      "symbol": "BTC/USDT",
      "position_type": "LONG",
      "entry_time": "2024-01-15T10:30:00",
      "exit_time": "2024-01-16T14:20:00",
      "entry_price": 45000.0,
      "exit_price": 46500.0,
      "quantity": 0.1,
      "stop_loss": 44000.0,
      "take_profit": 47000.0,
      "exit_reason": "TAKE_PROFIT",
      "pnl": 150.0,
      "pnl_pct": 3.33,
      "fees": 0.465,
      "cost_basis": 4500.0,
      "outcome": "WIN"
    },
    // ... 41 more trades
  ]
}
```

## Code Examples

### Python - Access from Backtest Results

```python
# After running a backtest
backtest_result = await real_backtesting_engine.run_backtest(...)

# Access detailed trades
closed_trades = backtest_result.get('closed_trades', [])

# Filter trades by outcome
winning_trades = [t for t in closed_trades if t['outcome'] == 'WIN']
losing_trades = [t for t in closed_trades if t['outcome'] == 'LOSS']

# Filter by exit reason
take_profit_trades = [t for t in closed_trades if t['exit_reason'] == 'TAKE_PROFIT']
stop_loss_trades = [t for t in closed_trades if t['exit_reason'] == 'STOP_LOSS']

# Get all LONG positions
long_trades = [t for t in closed_trades if t['position_type'] == 'LONG']

# Calculate average win/loss
avg_win = sum(t['pnl'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
avg_loss = sum(t['pnl'] for t in losing_trades) / len(losing_trades) if losing_trades else 0
```

### JavaScript/TypeScript - Frontend Access

```typescript
// Fetch detailed backtest results
const response = await fetch('/api/v1/strategies/backtest-results/{backtest_id}', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

const data = await response.json();

// Access all 42 trades
const trades = data.trades;

// Filter and analyze
const longTrades = trades.filter(t => t.position_type === 'LONG');
const shortTrades = trades.filter(t => t.position_type === 'SHORT');
const takeProfitExits = trades.filter(t => t.exit_reason === 'TAKE_PROFIT');
const stopLossExits = trades.filter(t => t.exit_reason === 'STOP_LOSS');

// Calculate metrics
const avgEntryPrice = trades.reduce((sum, t) => sum + t.entry_price, 0) / trades.length;
const avgExitPrice = trades.reduce((sum, t) => sum + t.exit_price, 0) / trades.length;
```

## Database Access

Trades are stored in the `backtest_results` table:

```sql
-- Get backtest with detailed trades
SELECT 
    id,
    strategy_id,
    strategy_name,
    total_trades,
    execution_params->'closed_trades' as detailed_trades
FROM backtest_results
WHERE user_id = 'your-user-id'
ORDER BY created_at DESC
LIMIT 10;

-- Count trades by exit reason
SELECT 
    strategy_id,
    jsonb_array_length(execution_params->'closed_trades') as total_trades,
    COUNT(*) FILTER (WHERE trade->>'exit_reason' = 'TAKE_PROFIT') as take_profit_count,
    COUNT(*) FILTER (WHERE trade->>'exit_reason' = 'STOP_LOSS') as stop_loss_count
FROM backtest_results,
     jsonb_array_elements(execution_params->'closed_trades') as trade
GROUP BY strategy_id;
```

## Implementation Details

### Enhanced Backtesting Engine

The `RealBacktestingEngine` now:
1. **Tracks positions** with entry details (stop_loss, take_profit, position_type)
2. **Monitors exits** - checks stop loss/take profit on each timestamp
3. **Creates complete trade records** when positions are closed
4. **Stores in database** - `execution_params.closed_trades` JSONB field

### Position Tracking

- **LONG positions**: Created on BUY signals
- **SHORT positions**: Created on SELL signals (if supported)
- **Multiple entries**: FIFO (First In, First Out) matching
- **Automatic exits**: Stop loss and take profit checked every timestamp

### Exit Reasons

- `TAKE_PROFIT`: Price hit take profit target
- `STOP_LOSS`: Price hit stop loss level
- `MANUAL`: Manual close via SELL signal
- `BACKTEST_END`: Position still open at end of backtest period

## Example: Get All 42 Trades

```bash
# Get backtest result ID first
curl -X GET "https://api.cryptouniverse.com/api/v1/strategies/backtest-results?strategy_id=momentum_strategy" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Then get detailed trades
curl -X GET "https://api.cryptouniverse.com/api/v1/strategies/backtest-results/{backtest_id}?include_trades=true" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

The response will include all trades in the `trades` array, each with complete entry/exit, stop loss, take profit, and position type information.

