"""Final trace to understand the issue"""

# If we have 600 assets but 0 opportunities, one of these must be true:
print("Possible scenarios for 600 assets but 0 opportunities:\n")

print("1. Asset structure mismatch:")
print("   - Assets are dicts, not AssetInfo objects")
print("   - Assets missing volume_24h_usd or symbol attributes")
print("   - Would cause AttributeError in _get_top_symbols_by_volume")
print("   - Scanner catches exception and returns empty list")
print()

print("2. Empty momentum_symbols:")
print("   - _get_top_symbols_by_volume returns empty list")
print("   - Scanner loop doesn't execute")
print("   - No opportunities generated")
print()

print("3. Scanner execution fails:")
print("   - momentum_symbols has symbols")
print("   - But trading_strategies_service.execute_strategy fails")
print("   - Each symbol fails, no opportunities added")
print()

# The key insight
print("The smoking gun:")
print("- We tested 'spot_momentum_strategy' directly and it works")
print("- But in discovery it generates 0 opportunities")
print("- This means momentum_symbols must be empty")
print("- Which means _get_top_symbols_by_volume is failing/returning empty")
print()

print("Most likely cause:")
print("The 600 assets are counted from cached data that has a different")
print("structure than what _get_top_symbols_by_volume expects.")