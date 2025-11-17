"""
Test Strategy Execution via API
Tests each strategy individually through the API endpoint to see what they return.
This matches how opportunity scanning calls strategies.
"""

import asyncio
import httpx
import json
import os
import sys
from typing import Dict, Any, Optional

# ⚠️ SECURITY WARNING: This test script must NEVER be run against production without proper safeguards.
# All credentials and URLs must be provided via environment variables to prevent accidental exposure.
# Environment variables are MANDATORY - the script will fail fast if they are not set.

BASE_URL = os.environ.get("TEST_BASE_URL")
EMAIL = os.environ.get("OPPORTUNITY_SCAN_TEST_EMAIL")
PASSWORD = os.environ.get("OPPORTUNITY_SCAN_TEST_PASSWORD")

if not all([BASE_URL, EMAIL, PASSWORD]):
    raise ValueError(
        "TEST_BASE_URL, OPPORTUNITY_SCAN_TEST_EMAIL, and OPPORTUNITY_SCAN_TEST_PASSWORD "
        "environment variables must be set. Never use default credentials against production."
    )

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


async def login(client: httpx.AsyncClient) -> Optional[str]:
    """Login and get access token."""
    print(f"\n[LOGIN] Logging in as {EMAIL}...")
    try:
        response = await client.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": EMAIL, "password": PASSWORD}
        )
        response.raise_for_status()
        data = response.json()
        token = data.get("access_token")
        if token:
            print(f"[OK] Login successful!")
            return token
        return None
    except Exception as e:
        print(f"[ERROR] Login failed: {e}")
        return None


async def test_strategy_execution(
    client: httpx.AsyncClient,
    token: str,
    function: str,
    **kwargs
) -> Dict[str, Any]:
    """Test a single strategy execution via API."""
    print(f"\n{'='*80}")
    print(f"Testing Strategy: {function}")
    print(f"{'='*80}")
    
    try:
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "function": function,
            "simulation_mode": True,
            **kwargs
        }
        
        print(f"\n📤 Request:")
        print(f"  Function: {function}")
        print(f"  Parameters: {json.dumps(kwargs, indent=2)}")
        
        response = await client.post(
            f"{BASE_URL}/api/v1/strategies/execute",
            json=payload,
            headers=headers,
            timeout=60.0
        )
        
        print(f"\n📥 Response Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return {"success": False, "error": f"HTTP {response.status_code}"}
        
        result = response.json()
        
        print(f"\n✅ Response received")
        print(f"Result Type: {type(result).__name__}")
        
        if isinstance(result, dict):
            execution_result = result.get("execution_result", {})
            success = execution_result.get("success") if execution_result else result.get("success", False)
            
            print(f"\n📊 Result Analysis:")
            print(f"  Top-level keys: {list(result.keys())}")
            print(f"  Success (execution_result): {execution_result.get('success') if execution_result else 'N/A'}")
            print(f"  Success (top-level): {result.get('success')}")
            print(f"  Credits used: {result.get('credits_used', 0)}")
            
            if execution_result:
                print(f"\n  Execution Result Keys: {list(execution_result.keys())}")
                
                # Check for common opportunity data structures
                if 'funding_arbitrage_analysis' in execution_result:
                    analysis = execution_result['funding_arbitrage_analysis']
                    opportunities = analysis.get('opportunities', []) if isinstance(analysis, dict) else []
                    print(f"  ✅ funding_arbitrage_analysis found")
                    print(f"     - opportunities count: {len(opportunities) if isinstance(opportunities, list) else 'NOT A LIST'}")
                    if opportunities and len(opportunities) > 0:
                        print(f"     - First opportunity keys: {list(opportunities[0].keys()) if isinstance(opportunities[0], dict) else 'NOT A DICT'}")
                
                if 'rebalancing_recommendations' in execution_result:
                    recs = execution_result['rebalancing_recommendations']
                    print(f"  ✅ rebalancing_recommendations found")
                    print(f"     - count: {len(recs) if isinstance(recs, list) else 'NOT A LIST'}")
                    if recs and len(recs) > 0:
                        print(f"     - First recommendation keys: {list(recs[0].keys()) if isinstance(recs[0], dict) else 'NOT A DICT'}")
                
                if 'risk_management_analysis' in execution_result:
                    risk_analysis = execution_result['risk_management_analysis']
                    print(f"  ✅ risk_management_analysis found")
                    if isinstance(risk_analysis, dict):
                        print(f"     - keys: {list(risk_analysis.keys())}")
                        if 'mitigation_strategies' in risk_analysis:
                            mitigations = risk_analysis['mitigation_strategies']
                            print(f"     - mitigation_strategies count: {len(mitigations) if isinstance(mitigations, list) else 'NOT A LIST'}")
                
                if 'signal' in execution_result:
                    signal = execution_result['signal']
                    print(f"  ✅ signal found")
                    if isinstance(signal, dict):
                        print(f"     - keys: {list(signal.keys())}")
                        print(f"     - strength: {signal.get('strength', 'NOT FOUND')}")
                        print(f"     - action: {signal.get('action', 'NOT FOUND')}")
                
                if 'trading_signals' in execution_result:
                    signals = execution_result['trading_signals']
                    print(f"  ✅ trading_signals found")
                    if isinstance(signals, dict):
                        print(f"     - keys: {list(signals.keys())}")
                        print(f"     - signal_strength: {signals.get('signal_strength', 'NOT FOUND')}")
                
                error = execution_result.get('error')
                if error:
                    print(f"\n  ❌ Error in execution_result: {error}")
            
            # Check top-level for error
            if result.get('error'):
                print(f"\n  ❌ Error at top-level: {result.get('error')}")
            
            # Print full structure (truncated)
            print(f"\n📋 Full Result Structure (first 3000 chars):")
            result_str = json.dumps(result, indent=2, default=str)
            print(result_str[:3000])
            if len(result_str) > 3000:
                print(f"\n... (truncated, total length: {len(result_str)} chars)")
            
            return result
        else:
            print(f"\n⚠️ Result is not a dictionary!")
            print(f"Result: {result}")
            return {"success": False, "error": "Invalid response type"}
            
    except httpx.TimeoutException:
        print(f"\n❌ Request timed out!")
        return {"success": False, "error": "timeout"}
    except Exception as e:
        print(f"\n❌ Exception during strategy execution:")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


async def main():
    """Test all strategies used in opportunity scanning."""
    
    print("="*80)
    print("STRATEGY EXECUTION TEST VIA API")
    print("Testing each strategy through the API endpoint")
    print("="*80)
    
    async with httpx.AsyncClient() as client:
        # Login
        token = await login(client)
        if not token:
            print("❌ Failed to login. Cannot proceed.")
            return
        
        # Test strategies used in opportunity scanning
        strategies_to_test = [
            {
                "function": "funding_arbitrage",
                "parameters": {
                    "symbols": "BTC/USDT,ETH/USDT",
                    "exchanges": "all",
                    "min_funding_rate": 0.005,
                }
            },
            {
                "function": "risk_management",
            },
            {
                "function": "portfolio_optimization",
            },
            {
                "function": "statistical_arbitrage",
                "strategy_type": "mean_reversion",
                "parameters": {"universe": "BTC/USDT,ETH/USDT"}
            },
            {
                "function": "pairs_trading",
                "strategy_type": "statistical_arbitrage",
                "parameters": {"pair_symbols": "BTC/USDT,ETH/USDT"}
            },
            {
                "function": "spot_momentum_strategy",
                "symbol": "BTC/USDT",
                "parameters": {"timeframe": "4h"}
            },
            {
                "function": "spot_mean_reversion",
                "symbol": "BTC/USDT",
                "parameters": {"timeframe": "1h"}
            },
            {
                "function": "spot_breakout_strategy",
                "symbol": "BTC/USDT",
                "parameters": {"timeframe": "1h"}
            },
        ]
        
        results_summary = []
        
        for strategy_config in strategies_to_test:
            function = strategy_config.pop("function")
            
            start_time = asyncio.get_event_loop().time()
            result = await test_strategy_execution(client, token, function, **strategy_config)
            elapsed = asyncio.get_event_loop().time() - start_time
            
            execution_result = result.get("execution_result", {}) if isinstance(result, dict) else {}
            success = execution_result.get("success") if execution_result else result.get("success", False)
            
            results_summary.append({
                "function": function,
                "success": success,
                "elapsed_seconds": elapsed,
                "has_error": bool(result.get("error") or execution_result.get("error") if isinstance(result, dict) else False)
            })
        
        # Print summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"\nTotal strategies tested: {len(results_summary)}")
        print(f"\nResults:")
        for result in results_summary:
            status = "✅ SUCCESS" if result['success'] else "❌ FAILED"
            error_indicator = " (HAS ERROR)" if result['has_error'] else ""
            print(f"  - {result['function']}: {status}{error_indicator} ({result['elapsed_seconds']:.2f}s)")
        
        successful = sum(1 for r in results_summary if r['success'])
        failed = len(results_summary) - successful
        print(f"\nSummary: {successful} successful, {failed} failed")
        print("="*80)


if __name__ == "__main__":
    asyncio.run(main())


