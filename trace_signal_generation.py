import numpy as np
import hashlib

def simulate_price_generation(symbol: str, periods: int = 100):
    """Simulate the price generation logic from market_analysis_core.py"""
    
    # Initial setup
    initial_price = 100.0
    prices = [initial_price]
    
    volatility = 0.03  # 3% daily volatility
    trend_bias = 0.0
    
    # Determine market cycle using symbol hash
    symbol_hash = hash(symbol) % 100
    
    if symbol_hash < 20:  # 20% bullish trend
        trend_bias = 0.001  # 0.1% upward bias per period
        volatility = 0.025  # Lower volatility in trends
    elif symbol_hash < 40:  # 20% bearish trend
        trend_bias = -0.001  # 0.1% downward bias
        volatility = 0.025
    elif symbol_hash < 60:  # 20% high volatility
        volatility = 0.05   # 5% volatility
        trend_bias = 0.0
    elif symbol_hash < 80:  # 20% accumulation phase
        volatility = 0.015  # Low volatility
        trend_bias = 0.0
    else:  # 20% breakout pattern
        volatility = 0.02
        trend_bias = 0.0
    
    # Generate price history with momentum
    momentum = 0  # Track short-term momentum
    
    np.random.seed(hash(symbol) % 1000000)  # Deterministic randomness
    
    for i in range(periods):
        # Add momentum factor (creates more realistic trends)
        momentum = momentum * 0.9 + np.random.uniform(-0.01, 0.01)
        
        # Generate price change with bias, volatility, and momentum
        change = (
            trend_bias +  # Long-term trend
            momentum +    # Short-term momentum
            np.random.normal(0, volatility)  # Random volatility
        )
        
        new_price = prices[-1] * (1 + change)
        prices.append(max(new_price, 0.01))  # Prevent negative prices
    
    return prices

def calculate_rsi(prices, period=14):
    """Calculate RSI"""
    if len(prices) < period + 1:
        if len(prices) >= 2:
            recent_change = (prices[-1] - prices[-2]) / prices[-2]
            rsi = 50 + (recent_change * 1000)
            return max(0, min(100, rsi))
        return 50.0
    
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    
    if avg_loss < 0.0001:
        return 100.0 if avg_gain > 0 else 50.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi

def calculate_ema(prices, period):
    """Calculate EMA"""
    if len(prices) < period:
        return np.mean(prices)
    
    multiplier = 2 / (period + 1)
    ema = np.mean(prices[:period])
    
    for price in prices[period:]:
        ema = (price * multiplier) + (ema * (1 - multiplier))
    
    return ema

# Test with different symbols
test_symbols = ["BTC", "ETH", "DOGE", "ADA", "SOL", "MATIC", "LINK", "DOT", "AVAX", "ATOM"]

print("Analyzing signal generation for different symbols:")
print("=" * 80)

bullish_signals = 0
bearish_signals = 0
hold_signals = 0

for symbol in test_symbols:
    prices = simulate_price_generation(symbol)
    
    # Calculate indicators
    rsi = calculate_rsi(prices)
    ema_12 = calculate_ema(prices, 12)
    ema_26 = calculate_ema(prices, 26)
    macd_line = ema_12 - ema_26
    macd_trend = "BULLISH" if macd_line > 0 else "BEARISH"
    
    # Apply momentum strategy logic
    signal_strength = 0
    action = "HOLD"
    
    if rsi > 60 and macd_trend == "BULLISH":
        signal_strength = 8
        action = "BUY"
        bullish_signals += 1
    elif rsi < 40 and macd_trend == "BEARISH":
        signal_strength = 8
        action = "SELL"
        bearish_signals += 1
    elif 45 <= rsi <= 55:
        signal_strength = 3
        action = "HOLD"
        hold_signals += 1
    else:
        signal_strength = 5
        action = "HOLD"
        hold_signals += 1
    
    print(f"\n{symbol}:")
    print(f"  Hash: {hash(symbol) % 100}")
    print(f"  RSI: {rsi:.2f}")
    print(f"  MACD: {macd_line:.4f} ({macd_trend})")
    print(f"  Signal: {action} (strength={signal_strength})")
    print(f"  Would generate opportunity: {'YES' if signal_strength >= 2.5 else 'NO'}")

print("\n" + "=" * 80)
print(f"Summary:")
print(f"  Bullish signals (strength=8): {bullish_signals}")
print(f"  Bearish signals (strength=8): {bearish_signals}")
print(f"  Hold signals: {hold_signals}")
print(f"  Total opportunities (strength >= 2.5): {bullish_signals + bearish_signals + hold_signals}")