"""Test what momentum_symbols actually contains"""

# Simulate the exact code from user_opportunity_discovery.py
def test_get_top_symbols_by_volume():
    # Test 1: What if discovered_assets is empty dict
    print("Test 1: Empty discovered_assets")
    discovered_assets = {}
    all_assets = []
    for tier_assets in discovered_assets.values():
        all_assets.extend(tier_assets)
    print(f"  all_assets: {all_assets}")
    print(f"  Length: {len(all_assets)}")
    
    # Test 2: What if discovered_assets has tiers but empty lists
    print("\nTest 2: Tiers with empty lists")
    discovered_assets = {
        "tier_institutional": [],
        "tier_enterprise": [],
        "tier_professional": [],
        "tier_retail": []
    }
    all_assets = []
    for tier_assets in discovered_assets.values():
        all_assets.extend(tier_assets)
    print(f"  all_assets: {all_assets}")
    print(f"  Length: {len(all_assets)}")
    
    # This would match "600 assets" but empty lists
    total = sum(len(assets) for assets in discovered_assets.values())
    print(f"  sum(len(assets)): {total}")
    
    # Test 3: What _get_top_symbols_by_volume would return
    print("\nTest 3: What _get_top_symbols_by_volume returns with empty all_assets")
    all_assets = []
    try:
        sorted_assets = sorted(all_assets, key=lambda x: x.volume_24h_usd, reverse=True)
        symbols = [asset.symbol for asset in sorted_assets[:30]]
        print(f"  momentum_symbols: {symbols}")
        print(f"  Length: {len(symbols)}")
        
        # This is what the scanner loop would see
        print(f"\nScanner loop:")
        for symbol in symbols:
            print(f"    Would process: {symbol}/USDT")
        if not symbols:
            print("    Loop would not execute - no symbols!")
    except Exception as e:
        print(f"  Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    test_get_top_symbols_by_volume()