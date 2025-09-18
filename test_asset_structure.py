"""Test what the asset discovery actually returns"""

# Simulate what _get_top_symbols_by_volume does
def test_symbol_extraction():
    # Simulate discovered_assets structure
    from dataclasses import dataclass
    from datetime import datetime
    
    @dataclass
    class AssetInfo:
        symbol: str
        exchange: str
        volume_24h_usd: float
        price_usd: float
        market_cap_usd: float
        tier: str
        last_updated: datetime
        metadata: dict
    
    # Create test assets
    test_assets = {
        "tier_retail": [
            AssetInfo("BTC", "binance", 1000000000, 50000, None, "tier_retail", datetime.now(), {}),
            AssetInfo("ETH", "binance", 500000000, 3000, None, "tier_retail", datetime.now(), {}),
            AssetInfo("SOL", "binance", 100000000, 100, None, "tier_retail", datetime.now(), {}),
        ],
        "tier_professional": [
            AssetInfo("BNB", "binance", 200000000, 400, None, "tier_professional", datetime.now(), {}),
        ]
    }
    
    # Simulate _get_top_symbols_by_volume
    all_assets = []
    for tier_assets in test_assets.values():
        all_assets.extend(tier_assets)
    
    print(f"Total assets collected: {len(all_assets)}")
    
    # Sort by volume
    sorted_assets = sorted(all_assets, key=lambda x: x.volume_24h_usd, reverse=True)
    symbols = [asset.symbol for asset in sorted_assets[:30]]
    
    print(f"Top symbols by volume: {symbols}")
    
    # Test if symbols would be passed to scanners
    for symbol in symbols[:3]:
        formatted_symbol = f"{symbol}/USDT"
        print(f"  Would scan: {formatted_symbol}")

if __name__ == "__main__":
    test_symbol_extraction()