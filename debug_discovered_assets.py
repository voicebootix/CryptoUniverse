#!/usr/bin/env python3

import asyncio
import sys
sys.path.append('/workspace')

from app.services.dynamic_asset_filter import DynamicAssetFilteringService

async def test_asset_discovery():
    service = DynamicAssetFilteringService()
    
    print("Testing asset discovery...")
    result = await service.discover_all_assets_with_volume_filtering(
        min_tier="tier_retail",
        force_refresh=True
    )
    
    print(f"\nResult type: {type(result)}")
    print(f"Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
    
    if isinstance(result, dict):
        for tier, assets in result.items():
            print(f"\n{tier}: {len(assets) if isinstance(assets, list) else type(assets)} assets")
            if isinstance(assets, list) and len(assets) > 0:
                print(f"  First asset: {assets[0] if hasattr(assets[0], '__dict__') else assets[0]}")
                if hasattr(assets[0], 'symbol'):
                    print(f"  Symbol attribute: {assets[0].symbol}")
                else:
                    print(f"  Asset structure: {type(assets[0])}, keys: {assets[0].keys() if isinstance(assets[0], dict) else 'Not a dict'}")

if __name__ == "__main__":
    asyncio.run(test_asset_discovery())