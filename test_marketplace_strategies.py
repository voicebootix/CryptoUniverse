"""
Test marketplace strategies to verify mock vs real data
"""
import asyncio
import json
from app.services.strategy_marketplace_service import strategy_marketplace_service
from app.services.trading_strategies import trading_strategies_service

async def test_marketplace_strategies():
    """Test all marketplace strategies for mock vs real data"""

    print("=" * 80)
    print("CRYPTO UNIVERSE MARKETPLACE STRATEGY ANALYSIS")
    print("Testing Mock Data vs Real Implementation")
    print("=" * 80)

    user_id = "test_admin_user"

    # 1. Get all marketplace strategies
    print("\n1. FETCHING ALL MARKETPLACE STRATEGIES...")
    marketplace_result = await strategy_marketplace_service.get_marketplace_strategies(
        user_id=user_id,
        include_ai_strategies=True,
        include_community_strategies=False
    )

    if not marketplace_result.get("success"):
        print(f"❌ Failed to get marketplace strategies: {marketplace_result.get('error')}")
        return

    strategies = marketplace_result.get("strategies", [])
    print(f"✅ Found {len(strategies)} AI strategies in marketplace")

    # 2. Test each strategy
    print("\n2. TESTING EACH STRATEGY FOR MOCK DATA...")
    print("-" * 80)

    mock_data_strategies = []
    real_data_strategies = []
    partial_mock_strategies = []

    for strategy in strategies[:10]:  # Test first 10 strategies
        strategy_id = strategy["strategy_id"]
        strategy_name = strategy["name"]
        strategy_func = strategy_id.replace("ai_", "")

        print(f"\n📊 Testing: {strategy_name} ({strategy_id})")

        # Test 1: Check performance data
        performance = strategy.get("live_performance", {})
        if not performance or performance.get("total_pnl") == 500.0:
            print("  ⚠️  Performance: DEFAULT/MOCK (500.0 PnL fallback)")
            mock_indicator = True
        else:
            print(f"  ✓ Performance: {performance.get('total_pnl', 0):.2f} PnL")
            mock_indicator = False

        # Test 2: Check backtest results
        backtest = strategy.get("backtest_results", {})
        if not backtest or "calculation_method" not in backtest:
            print("  ⚠️  Backtest: MISSING")
            backtest_mock = True
        elif backtest.get("calculation_method") == "realistic_strategy_profile":
            print("  ⚠️  Backtest: SYNTHETIC (pre-defined profile)")
            backtest_mock = True
        elif backtest.get("calculation_method") == "real_historical_simulation":
            print("  ✓ Backtest: REAL (historical simulation)")
            backtest_mock = False
        else:
            print(f"  ? Backtest: UNKNOWN ({backtest.get('calculation_method')})")
            backtest_mock = True

        # Test 3: Actually call the strategy function
        print(f"  🔄 Executing strategy function...")
        try:
            result = await trading_strategies_service.execute_strategy_function(
                function_name=strategy_func,
                params={
                    "user_id": user_id,
                    "symbol": "BTC",
                    "amount": 100,
                    "simulation_mode": True
                }
            )

            if result.get("success"):
                # Check if result contains mock indicators
                if "mock_data" in str(result).lower() or "sample" in str(result).lower():
                    print("  ⚠️  Execution: MOCK DATA DETECTED")
                    execution_mock = True
                elif result.get("data", {}).get("source") == "mock":
                    print("  ⚠️  Execution: MOCK SOURCE")
                    execution_mock = True
                else:
                    print("  ✓ Execution: APPEARS REAL")
                    execution_mock = False
            else:
                print(f"  ❌ Execution: FAILED - {result.get('error')}")
                execution_mock = True
        except Exception as e:
            print(f"  ❌ Execution: ERROR - {str(e)}")
            execution_mock = True

        # Categorize strategy
        if mock_indicator and backtest_mock and execution_mock:
            mock_data_strategies.append(strategy_name)
        elif not mock_indicator and not backtest_mock and not execution_mock:
            real_data_strategies.append(strategy_name)
        else:
            partial_mock_strategies.append(strategy_name)

    # 3. Summary Report
    print("\n" + "=" * 80)
    print("ANALYSIS SUMMARY")
    print("=" * 80)

    print(f"\n🔴 FULLY MOCK STRATEGIES ({len(mock_data_strategies)}):")
    for s in mock_data_strategies:
        print(f"  - {s}")

    print(f"\n🟡 PARTIAL MOCK STRATEGIES ({len(partial_mock_strategies)}):")
    for s in partial_mock_strategies:
        print(f"  - {s}")

    print(f"\n🟢 REAL DATA STRATEGIES ({len(real_data_strategies)}):")
    for s in real_data_strategies:
        print(f"  - {s}")

    # 4. Test historical data generation
    print("\n" + "=" * 80)
    print("TESTING HISTORICAL DATA GENERATION")
    print("=" * 80)

    from app.services.market_analysis_core import market_analysis_service

    print("\n🔍 Testing _get_historical_price_data...")
    historical_data = await market_analysis_service._get_historical_price_data(
        symbol="BTC",
        timeframe="1h",
        periods=10
    )

    if historical_data:
        print(f"✅ Generated {len(historical_data)} candles")
        first_candle = historical_data[0]
        last_candle = historical_data[-1]
        print(f"  First: {first_candle['close']:.2f} at {first_candle['timestamp']}")
        print(f"  Last:  {last_candle['close']:.2f} at {last_candle['timestamp']}")

        # Check for synthetic patterns
        prices = [c['close'] for c in historical_data]
        price_changes = [abs(prices[i] - prices[i-1])/prices[i-1] for i in range(1, len(prices))]
        avg_change = sum(price_changes) / len(price_changes)

        if avg_change < 0.001:
            print("  ⚠️  WARNING: Prices show almost no movement (likely static)")
        elif all(pc < 0.1 for pc in price_changes):
            print("  ✓ Price movements appear realistic")
        else:
            print("  ⚠️  WARNING: Extreme price movements detected")
    else:
        print("❌ No historical data generated")

    # 5. Test trade execution simulation
    print("\n" + "=" * 80)
    print("TESTING TRADE EXECUTION")
    print("=" * 80)

    from app.services.trade_execution import trade_execution_service

    print("\n🔍 Testing simulation mode execution...")

    # Create trade request dict as expected by function signature
    trade_request = {
        "symbol": "BTC",
        "side": "buy",
        "quantity": 0.01,
        "order_type": "market"
    }

    trade_result = await trade_execution_service.execute_trade(
        trade_request, user_id, True  # trade_request, user_id, simulation_mode
    )

    if trade_result.get("success"):
        sim_result = trade_result.get("simulation_result", {})
        print("✅ Simulation execution successful")
        print(f"  Order ID: {sim_result.get('order_id')}")
        print(f"  Fill Rate: {sim_result.get('quantity', 0) / 0.01:.2%}")
        print(f"  Slippage: {sim_result.get('slippage_bps', 0)} bps")

        if "SIM_" in sim_result.get("order_id", ""):
            print("  ✓ Correctly marked as simulation")
        else:
            print("  ⚠️  Not properly marked as simulation")
    else:
        print(f"❌ Simulation failed: {trade_result.get('error')}")

    print("\n" + "=" * 80)
    print("FINAL VERDICT")
    print("=" * 80)

    total_tested = len(mock_data_strategies) + len(partial_mock_strategies) + len(real_data_strategies)
    mock_percentage = (len(mock_data_strategies) / total_tested * 100) if total_tested > 0 else 0

    print(f"\n📊 Mock Data Percentage: {mock_percentage:.1f}%")

    if mock_percentage > 75:
        print("🔴 VERDICT: Platform is primarily using MOCK DATA")
        print("   - Performance metrics are synthetic")
        print("   - Backtests use generated profiles")
        print("   - Historical data is fabricated")
        print("   - Trade execution is simulated")
    elif mock_percentage > 25:
        print("🟡 VERDICT: Platform uses MIXED mock and real data")
        print("   - Some strategies have real implementations")
        print("   - Historical data generation is deterministic")
        print("   - Trade simulation is properly marked")
    else:
        print("🟢 VERDICT: Platform primarily uses REAL DATA")
        print("   - Most strategies have real implementations")
        print("   - Data sources are legitimate")
        print("   - Execution paths are production-ready")

if __name__ == "__main__":
    asyncio.run(test_marketplace_strategies())