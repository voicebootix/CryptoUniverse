import random
import math

def simulate_rsi_macd_for_symbol(symbol: str):
    """Simulate what RSI and MACD might be for a symbol based on the market analysis logic"""
    
    # Determine market cycle using symbol hash (same as in market_analysis_core.py)
    symbol_hash = hash(symbol) % 100
    
    market_condition = ""
    if symbol_hash < 20:  # 20% bullish trend
        market_condition = "BULLISH TREND"
        # In a bullish trend with 0.1% upward bias, RSI tends to be higher
        # But with volatility, it might not always be > 60
        estimated_rsi = 55 + random.uniform(-10, 15)  # 45-70 range
        macd_likely_positive = True
    elif symbol_hash < 40:  # 20% bearish trend
        market_condition = "BEARISH TREND"
        estimated_rsi = 45 + random.uniform(-15, 10)  # 30-55 range
        macd_likely_positive = False
    elif symbol_hash < 60:  # 20% high volatility
        market_condition = "HIGH VOLATILITY"
        estimated_rsi = 50 + random.uniform(-20, 20)  # 30-70 range
        macd_likely_positive = random.choice([True, False])
    elif symbol_hash < 80:  # 20% accumulation phase
        market_condition = "ACCUMULATION"
        estimated_rsi = 50 + random.uniform(-5, 5)  # 45-55 range
        macd_likely_positive = random.choice([True, False])
    else:  # 20% breakout pattern
        market_condition = "BREAKOUT"
        estimated_rsi = 50 + random.uniform(-10, 10)  # 40-60 range
        macd_likely_positive = random.choice([True, False])
    
    # Clamp RSI
    estimated_rsi = max(0, min(100, estimated_rsi))
    
    # MACD trend
    macd_trend = "BULLISH" if macd_likely_positive else "BEARISH"
    
    # Apply momentum strategy logic
    signal_strength = 0
    action = "HOLD"
    
    if estimated_rsi > 60 and macd_trend == "BULLISH":
        signal_strength = 8
        action = "BUY"
    elif estimated_rsi < 40 and macd_trend == "BEARISH":
        signal_strength = 8
        action = "SELL"
    elif 45 <= estimated_rsi <= 55:
        signal_strength = 3
        action = "HOLD"
    else:
        signal_strength = 5
        action = "HOLD"
    
    return {
        "symbol": symbol,
        "hash": symbol_hash,
        "market_condition": market_condition,
        "rsi": estimated_rsi,
        "macd_trend": macd_trend,
        "signal_strength": signal_strength,
        "action": action,
        "generates_opportunity": signal_strength >= 2.5
    }

# Test with symbols that would be scanned
test_symbols = ["BTC", "ETH", "BNB", "SOL", "ADA", "DOGE", "AVAX", "DOT", "MATIC", "LINK",
                "UNI", "ATOM", "LTC", "BCH", "ALGO", "VET", "FIL", "ICP", "SAND", "MANA",
                "AXS", "THETA", "XLM", "TRX", "EOS", "AAVE", "SUSHI", "COMP", "YFI", "MKR"]

print("Signal Generation Analysis")
print("=" * 100)
print(f"{'Symbol':<6} {'Hash':<4} {'Market Condition':<15} {'RSI':<6} {'MACD':<8} {'Signal':<6} {'Strength':<8} {'Opportunity?'}")
print("-" * 100)

opportunities_count = 0
buy_signals = 0
sell_signals = 0

for symbol in test_symbols:
    result = simulate_rsi_macd_for_symbol(symbol)
    
    print(f"{result['symbol']:<6} {result['hash']:<4} {result['market_condition']:<15} "
          f"{result['rsi']:>6.1f} {result['macd_trend']:<8} {result['action']:<6} "
          f"{result['signal_strength']:<8} {'YES' if result['generates_opportunity'] else 'NO'}")
    
    if result['generates_opportunity']:
        opportunities_count += 1
        if result['action'] == "BUY":
            buy_signals += 1
        elif result['action'] == "SELL":
            sell_signals += 1

print("\n" + "=" * 100)
print(f"Summary:")
print(f"  Total symbols tested: {len(test_symbols)}")
print(f"  Opportunities generated: {opportunities_count}")
print(f"  Buy signals: {buy_signals}")
print(f"  Sell signals: {sell_signals}")
print(f"  Opportunity rate: {opportunities_count/len(test_symbols)*100:.1f}%")

print("\n🔍 ROOT CAUSE ANALYSIS:")
print("The issue is that the momentum strategy requires BOTH conditions to generate strong signals:")
print("  - BUY: RSI > 60 AND MACD = BULLISH")
print("  - SELL: RSI < 40 AND MACD = BEARISH")
print("\nWith realistic market simulation, these conditions rarely align perfectly!")
print("Most symbols end up with RSI near 50 and mixed MACD signals.")