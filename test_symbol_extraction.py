"""Test the exact symbol extraction logic"""

def test_symbol_extraction_with_error_handling():
    # Test Case 1: Empty discovered_assets
    print("Test 1: Empty discovered_assets")
    discovered_assets = {}
    all_assets = []
    for tier_assets in discovered_assets.values():
        all_assets.extend(tier_assets)
    print(f"  all_assets length: {len(all_assets)}")
    
    # Test Case 2: Assets as dicts without volume_24h_usd
    print("\nTest 2: Assets without volume_24h_usd attribute")
    discovered_assets = {
        "tier_retail": [
            {"symbol": "BTC", "price": 50000},  # Missing volume_24h_usd
            {"symbol": "ETH", "price": 3000}
        ]
    }
    all_assets = []
    for tier_assets in discovered_assets.values():
        all_assets.extend(tier_assets)
    
    try:
        sorted_assets = sorted(all_assets, key=lambda x: x.volume_24h_usd, reverse=True)
        print(f"  Sorting succeeded: {len(sorted_assets)} assets")
    except AttributeError as e:
        print(f"  AttributeError: {e}")
    except Exception as e:
        print(f"  Other error: {type(e).__name__}: {e}")
    
    # Test Case 3: Assets as objects with volume_24h_usd
    print("\nTest 3: Assets with proper attributes")
    class MockAsset:
        def __init__(self, symbol, volume):
            self.symbol = symbol
            self.volume_24h_usd = volume
    
    discovered_assets = {
        "tier_retail": [
            MockAsset("BTC", 1000000000),
            MockAsset("ETH", 500000000)
        ]
    }
    all_assets = []
    for tier_assets in discovered_assets.values():
        all_assets.extend(tier_assets)
    
    try:
        sorted_assets = sorted(all_assets, key=lambda x: x.volume_24h_usd, reverse=True)
        symbols = [asset.symbol for asset in sorted_assets[:30]]
        print(f"  Success! Got symbols: {symbols}")
    except Exception as e:
        print(f"  Error: {type(e).__name__}: {e}")
    
    # Test Case 4: What happens in scanner with exception
    print("\nTest 4: Scanner with exception handling")
    try:
        discovered_assets = {
            "tier_retail": [{"symbol": "BTC"}]  # Missing volume_24h_usd
        }
        all_assets = []
        for tier_assets in discovered_assets.values():
            all_assets.extend(tier_assets)
        
        sorted_assets = sorted(all_assets, key=lambda x: x.volume_24h_usd, reverse=True)
        symbols = [asset.symbol for asset in sorted_assets[:30]]
        print(f"  Got {len(symbols)} symbols")
    except Exception as e:
        print(f"  Scanner would catch: {type(e).__name__}: {e}")
        print(f"  Scanner would return empty list")

if __name__ == "__main__":
    test_symbol_extraction_with_error_handling()