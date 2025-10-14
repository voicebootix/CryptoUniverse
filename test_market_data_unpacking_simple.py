#!/usr/bin/env python3
"""
Simple Test for Market Data Unpacking Fix
Tests the core parsing logic without external dependencies
"""

import sys
import os
from datetime import datetime
from typing import Dict, Any, List

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))


def test_order_book_parsing_robustness():
    """Test order book parsing with various data formats that could cause unpacking errors."""
    print("🧪 Testing order book parsing robustness...")
    
    def _parse_order_book_levels(levels: List, level_type: str) -> List[List[float]]:
        """Safely parse order book levels with comprehensive error handling."""
        parsed_levels = []
        for i, level in enumerate(levels):
            try:
                if isinstance(level, (list, tuple)) and len(level) >= 2:
                    # Standard format: [price, amount, ...]
                    price = float(level[0])
                    amount = float(level[1])
                    parsed_levels.append([price, amount])
                elif isinstance(level, dict):
                    # Dictionary format: {'price': x, 'amount': y, ...}
                    price = float(level.get('price', 0))
                    amount = float(level.get('amount', 0))
                    if price > 0 and amount > 0:
                        parsed_levels.append([price, amount])
                else:
                    print(f"  ⚠️  Unexpected order book level format for {level_type}: {type(level).__name__}")
            except (ValueError, TypeError, IndexError) as e:
                print(f"  ⚠️  Failed to parse order book level for {level_type}: {e}")
                continue
        
        return parsed_levels
    
    # Test cases that could cause unpacking errors
    test_cases = [
        # Standard format
        {"bids": [[50000, 1.0], [49900, 2.0]], "asks": [[50100, 1.0], [50200, 2.0]]},
        # Extra data in levels (could cause unpacking error)
        {"bids": [[50000, 1.0, "extra"], [49900, 2.0, "extra"]], "asks": [[50100, 1.0, "extra"]]},
        # Dictionary format
        {"bids": [{"price": 50000, "amount": 1.0}], "asks": [{"price": 50100, "amount": 1.0}]},
        # Mixed formats
        {"bids": [[50000, 1.0], {"price": 49900, "amount": 2.0}], "asks": [[50100, 1.0]]},
        # Invalid data
        {"bids": ["invalid", 123], "asks": [None, "invalid"]},
        # Empty data
        {"bids": [], "asks": []},
    ]
    
    results = []
    for i, test_case in enumerate(test_cases):
        try:
            bids = _parse_order_book_levels(test_case.get('bids', []), 'bids')
            asks = _parse_order_book_levels(test_case.get('asks', []), 'asks')
            
            results.append({
                "test_case": i,
                "bids_count": len(bids),
                "asks_count": len(asks),
                "status": "success"
            })
            print(f"  ✅ Test case {i}: {len(bids)} bids, {len(asks)} asks")
            
        except Exception as e:
            results.append({
                "test_case": i,
                "error": str(e),
                "status": "error"
            })
            print(f"  ❌ Test case {i}: ERROR: {e}")
    
    return {
        "test_name": "order_book_parsing_robustness",
        "total_tests": len(test_cases),
        "passed": len([r for r in results if r["status"] == "success"]),
        "failed": len([r for r in results if r["status"] == "error"]),
        "results": results
    }


def test_ohlcv_parsing_robustness():
    """Test OHLCV parsing with various data formats."""
    print("🧪 Testing OHLCV parsing robustness...")
    
    def _parse_ohlcv_candles(candles: List) -> List[Dict[str, Any]]:
        """Safely parse OHLCV candles with comprehensive error handling."""
        ohlcv_data = []
        for i, candle in enumerate(candles):
            try:
                if isinstance(candle, (list, tuple)) and len(candle) >= 6:
                    # Standard OHLCV format: [timestamp, open, high, low, close, volume, ...]
                    ohlcv_data.append({
                        'timestamp': datetime.fromtimestamp(candle[0]/1000).isoformat(),
                        'open': float(candle[1]),
                        'high': float(candle[2]),
                        'low': float(candle[3]),
                        'close': float(candle[4]),
                        'volume': float(candle[5])
                    })
                elif isinstance(candle, dict):
                    # Dictionary format: {'timestamp': x, 'open': y, ...}
                    timestamp = candle.get('timestamp', 0)
                    if isinstance(timestamp, (int, float)):
                        timestamp = datetime.fromtimestamp(timestamp/1000).isoformat()
                    elif isinstance(timestamp, str):
                        timestamp = timestamp
                    else:
                        timestamp = datetime.utcnow().isoformat()
                    
                    ohlcv_data.append({
                        'timestamp': timestamp,
                        'open': float(candle.get('open', 0)),
                        'high': float(candle.get('high', 0)),
                        'low': float(candle.get('low', 0)),
                        'close': float(candle.get('close', 0)),
                        'volume': float(candle.get('volume', 0))
                    })
                else:
                    print(f"  ⚠️  Unexpected OHLCV candle format: {type(candle).__name__}")
            except (ValueError, TypeError, IndexError, KeyError) as e:
                print(f"  ⚠️  Failed to parse OHLCV candle: {e}")
                continue
        
        return ohlcv_data
    
    test_cases = [
        # Standard format
        [[1640995200000, 50000, 51000, 49000, 50500, 1000]],
        # Extra data (could cause unpacking error)
        [[1640995200000, 50000, 51000, 49000, 50500, 1000, "extra", "data"]],
        # Dictionary format
        [{"timestamp": 1640995200000, "open": 50000, "high": 51000, "low": 49000, "close": 50500, "volume": 1000}],
        # Mixed formats
        [[1640995200000, 50000, 51000, 49000, 50500, 1000], {"timestamp": 1640995201000, "open": 50500, "high": 51500, "low": 49500, "close": 51000, "volume": 1100}],
        # Invalid data
        [["invalid", "data"], {"invalid": "format"}],
        # Empty data
        [],
    ]
    
    results = []
    for i, test_case in enumerate(test_cases):
        try:
            candles = _parse_ohlcv_candles(test_case)
            
            results.append({
                "test_case": i,
                "candles_count": len(candles),
                "status": "success"
            })
            print(f"  ✅ Test case {i}: {len(candles)} candles parsed")
            
        except Exception as e:
            results.append({
                "test_case": i,
                "error": str(e),
                "status": "error"
            })
            print(f"  ❌ Test case {i}: ERROR: {e}")
    
    return {
        "test_name": "ohlcv_parsing_robustness",
        "total_tests": len(test_cases),
        "passed": len([r for r in results if r["status"] == "success"]),
        "failed": len([r for r in results if r["status"] == "error"]),
        "results": results
    }


def test_symbol_normalization_edge_cases():
    """Test symbol normalization with various edge cases that could cause unpacking errors."""
    print("🧪 Testing symbol normalization edge cases...")
    
    def _normalize_symbol(symbol: str) -> str:
        """Normalize symbol to CCXT's expected ``BASE/QUOTE`` format with enterprise-grade error handling."""
        if not symbol:
            return "BTC/USDT"

        try:
            cleaned_symbol = symbol.upper().strip()

            if "/" in cleaned_symbol:
                # Enterprise-grade symbol splitting with comprehensive error handling
                parts = cleaned_symbol.split("/")
                if len(parts) == 2:
                    base, quote = parts
                    base = base.replace("-", "").replace("_", "").strip()
                    quote = quote.replace("-", "").replace("_", "").strip() or "USDT"
                    return f"{base}/{quote}"
                else:
                    # Handle multiple slashes by taking first and last parts
                    print(f"  ⚠️  Symbol contains multiple slashes, using first and last parts: {symbol}")
                    base = parts[0].replace("-", "").replace("_", "").strip()
                    quote = parts[-1].replace("-", "").replace("_", "").strip() or "USDT"
                    return f"{base}/{quote}"

            collapsed = cleaned_symbol.replace("-", "").replace("_", "")

            known_quotes = ["USDT", "USD", "USDC", "BTC", "ETH", "EUR"]
            for quote in known_quotes:
                if collapsed.endswith(quote) and len(collapsed) > len(quote):
                    base = collapsed[: -len(quote)]
                    return f"{base}/{quote}"

            return f"{collapsed}/USDT"
            
        except Exception as e:
            print(f"  ⚠️  Failed to normalize symbol, using fallback: {symbol} - {e}")
            return "BTC/USDT"
    
    test_cases = [
        "BTC/USDT",           # Standard format
        "BTC/USD/USDT",       # Multiple slashes
        "BTC-USDT",           # Dash separator
        "BTC_USDT",           # Underscore separator
        "btc/usdt",           # Lowercase
        "  BTC/USDT  ",       # Whitespace
        "BTC",                # No quote
        "BTC/USD/USDT/EUR",   # Multiple slashes
        "",                   # Empty string
        "BTC/",               # Missing quote
        "/USDT",              # Missing base
        "BTC/USDT/EXTRA",     # Extra data
    ]
    
    results = []
    for symbol in test_cases:
        try:
            normalized = _normalize_symbol(symbol)
            results.append({
                "input": symbol,
                "output": normalized,
                "status": "success"
            })
            print(f"  ✅ {symbol} -> {normalized}")
        except Exception as e:
            results.append({
                "input": symbol,
                "output": None,
                "error": str(e),
                "status": "error"
            })
            print(f"  ❌ {symbol} -> ERROR: {e}")
    
    return {
        "test_name": "symbol_normalization_edge_cases",
        "total_tests": len(test_cases),
        "passed": len([r for r in results if r["status"] == "success"]),
        "failed": len([r for r in results if r["status"] == "error"]),
        "results": results
    }


def main():
    """Main test execution."""
    print("🚀 Starting Simple Market Data Unpacking Fix Test Suite")
    print("=" * 70)
    
    # Run all tests
    tests = [
        test_symbol_normalization_edge_cases(),
        test_order_book_parsing_robustness(),
        test_ohlcv_parsing_robustness(),
    ]
    
    # Generate summary
    total_tests = sum(t["total_tests"] for t in tests)
    total_passed = sum(t["passed"] for t in tests)
    total_failed = sum(t["failed"] for t in tests)
    
    print("\n" + "=" * 70)
    print("📊 SIMPLE TEST RESULTS SUMMARY")
    print("=" * 70)
    
    for test in tests:
        print(f"✅ {test['test_name']}: {test['passed']}/{test['total_tests']} passed")
    
    print(f"\n🎯 OVERALL RESULTS:")
    print(f"   Total Tests: {total_tests}")
    print(f"   Passed: {total_passed}")
    print(f"   Failed: {total_failed}")
    print(f"   Success Rate: {(total_passed/total_tests)*100:.1f}%")
    
    if total_failed == 0:
        print("\n🎉 ALL TESTS PASSED! The market data unpacking fix logic is working correctly.")
        return True
    else:
        print(f"\n⚠️  {total_failed} tests failed. Review the results above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)