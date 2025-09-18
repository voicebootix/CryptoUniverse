"""Test the exact scanner flow"""

# Simulate what happens in the scanner
def test_scanner_symbol_extraction():
    print("=== TESTING EXACT SCANNER FLOW ===\n")
    
    # Scenario 1: What if discovered_assets looks valid but assets are wrong type
    class FakeAsset:
        def __init__(self, data):
            # Simulating if asset is a dict wrapped in an object
            self.data = data
            
    discovered_assets = {
        "tier_retail": [
            FakeAsset({"symbol": "BTC", "volume_24h_usd": 1000000}),
            FakeAsset({"symbol": "ETH", "volume_24h_usd": 500000})
        ],
        "tier_professional": [
            FakeAsset({"symbol": "SOL", "volume_24h_usd": 100000})
        ]
    }
    
    # Count assets (this would show 3)
    total = sum(len(assets) for assets in discovered_assets.values())
    print(f"Total assets counted: {total}")
    
    # Try to extract symbols
    print("\nTrying _get_top_symbols_by_volume logic:")
    all_assets = []
    for tier_assets in discovered_assets.values():
        all_assets.extend(tier_assets)
    print(f"all_assets length: {len(all_assets)}")
    
    try:
        # This would fail because FakeAsset doesn't have volume_24h_usd attribute
        sorted_assets = sorted(all_assets, key=lambda x: x.volume_24h_usd, reverse=True)
        symbols = [asset.symbol for asset in sorted_assets[:30]]
        print(f"Success! Got {len(symbols)} symbols")
    except AttributeError as e:
        print(f"AttributeError: {e}")
        print("Scanner would return empty list!")
        symbols = []
    
    print(f"\nmomentum_symbols would be: {symbols}")
    print(f"Scanner loop would execute {len(symbols)} times")
    
    # Scenario 2: What if discovered_assets has proper structure but is actually a defaultdict
    print("\n\nScenario 2: defaultdict that returns empty lists")
    from collections import defaultdict
    
    discovered_assets = defaultdict(list)
    # This would still have keys when converted to dict
    discovered_assets["tier_retail"]  # Access creates empty list
    discovered_assets["tier_professional"]
    discovered_assets["tier_enterprise"] 
    discovered_assets["tier_institutional"]
    
    print(f"Keys exist: {list(discovered_assets.keys())}")
    total = sum(len(assets) for assets in discovered_assets.values())
    print(f"But total assets: {total}")
    
    # The smoking gun - this matches our symptoms!
    # Keys exist (shows tiers) but lists are empty (0 assets processed)

if __name__ == "__main__":
    test_scanner_symbol_extraction()