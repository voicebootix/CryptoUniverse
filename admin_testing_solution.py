#!/usr/bin/env python3
"""
Admin Testing Solution

Simple approach: Test strategies directly via execute endpoint
without needing to purchase them first.

Environment Variables Required:
- BASE_URL: API base URL (e.g., https://cryptouniverse.onrender.com/api/v1)
- ADMIN_EMAIL: Admin user email for authentication
- ADMIN_PASSWORD: Admin user password for authentication

Set these in your local .env file or CI secrets. Do not hardcode in source.
"""

import requests
import json
import time
import os
import sys
from typing import Optional

def _get_required_env_var(var_name: str, description: str) -> str:
    """
    Securely load required environment variable with validation.
    
    Args:
        var_name: Environment variable name
        description: Human-readable description for error messages
        
    Returns:
        Environment variable value
        
    Raises:
        SystemExit: If environment variable is missing or empty
    """
    value = os.getenv(var_name)
    
    if not value or not value.strip():
        print(f"❌ ERROR: Required environment variable '{var_name}' is missing or empty")
        print(f"   Description: {description}")
        print(f"   Please set {var_name} in your .env file or environment")
        print(f"   Example: export {var_name}='your_value_here'")
        sys.exit(1)
    
    # Do not log the actual value for security
    print(f"✅ Loaded {var_name} from environment")
    return value.strip()

# Load configuration from environment variables (validated at import)
BASE_URL = _get_required_env_var("BASE_URL", "API base URL for testing")
ADMIN_EMAIL = _get_required_env_var("ADMIN_EMAIL", "Admin user email for authentication") 
ADMIN_PASSWORD = _get_required_env_var("ADMIN_PASSWORD", "Admin user password for authentication")

# Validate BASE_URL format
if not BASE_URL.startswith(("http://", "https://")):
    print(f"❌ ERROR: BASE_URL must start with http:// or https://")
    print(f"   Current value starts with: {BASE_URL[:10]}...")
    sys.exit(1)

def test_all_strategies_directly():
    """Test all 25 strategies directly via execute endpoint."""
    
    print("🔧 ADMIN STRATEGY TESTING - DIRECT EXECUTION")
    print("=" * 70)
    
    # Robust authentication with retries and validation
    session = requests.Session()
    
    def authenticate_with_retry() -> str:
        """Authenticate with retry logic and robust validation."""
        login_data = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        max_attempts = 3
        base_delay = 1.0
        
        for attempt in range(max_attempts):
            try:
                print(f"🔐 Authentication attempt {attempt + 1}/{max_attempts}")
                
                response = session.post(
                    f"{BASE_URL}/auth/login", 
                    json=login_data,
                    timeout=10.0  # 10 second timeout
                )
                
                # Check HTTP status
                if not response.ok:
                    error_msg = f"HTTP {response.status_code}"
                    try:
                        error_data = response.json()
                        error_msg += f": {error_data.get('detail', response.text[:100])}"
                    except:
                        error_msg += f": {response.text[:100]}"
                    
                    if attempt < max_attempts - 1 and response.status_code >= 500:
                        print(f"   ⚠️ Server error ({error_msg}), retrying in {base_delay * (attempt + 1)}s...")
                        time.sleep(base_delay * (attempt + 1))
                        continue
                    else:
                        print(f"❌ Authentication failed: {error_msg}")
                        sys.exit(1)
                
                # Parse and validate response
                try:
                    auth_data = response.json()
                except json.JSONDecodeError as e:
                    print(f"❌ Invalid JSON response: {e}")
                    sys.exit(1)
                
                # Validate access token
                access_token = auth_data.get("access_token")
                if not access_token or not access_token.strip():
                    print(f"❌ No access token in response")
                    print(f"   Response keys: {list(auth_data.keys())}")
                    sys.exit(1)
                
                # Validate token format (basic check)
                if len(access_token.strip()) < 10:
                    print(f"❌ Access token appears invalid (too short)")
                    sys.exit(1)
                
                print(f"✅ Authentication successful")
                return access_token.strip()
                
            except requests.exceptions.Timeout:
                if attempt < max_attempts - 1:
                    print(f"   ⚠️ Request timeout, retrying in {base_delay * (attempt + 1)}s...")
                    time.sleep(base_delay * (attempt + 1))
                    continue
                else:
                    print(f"❌ Authentication failed: Request timeout after {max_attempts} attempts")
                    sys.exit(1)
                    
            except requests.exceptions.RequestException as e:
                if attempt < max_attempts - 1:
                    print(f"   ⚠️ Network error ({e}), retrying in {base_delay * (attempt + 1)}s...")
                    time.sleep(base_delay * (attempt + 1))
                    continue
                else:
                    print(f"❌ Authentication failed: Network error after {max_attempts} attempts: {e}")
                    sys.exit(1)
        
        print(f"❌ Authentication failed after {max_attempts} attempts")
        sys.exit(1)
    
    # Authenticate and set headers
    token = authenticate_with_retry()
    session.headers.update({"Authorization": f"Bearer {token}"})
    
    # All 25 strategy functions to test
    all_strategy_functions = [
        # Derivatives (12)
        {"function": "futures_trade", "params": {"strategy_type": "long_futures", "leverage": 3}},
        {"function": "options_trade", "params": {"strategy_type": "call_option", "strike_price": 50000}},
        {"function": "perpetual_trade", "params": {"leverage": 5}},
        {"function": "leverage_position", "params": {"leverage": 3, "position_size": 1000}},
        {"function": "complex_strategy", "params": {"strategy_type": "iron_condor"}},
        {"function": "margin_status", "params": {}},
        {"function": "funding_arbitrage", "params": {"symbols": "BTC,ETH"}},
        {"function": "basis_trade", "params": {}},
        {"function": "options_chain", "params": {"expiry_date": "2024-12-27"}},
        {"function": "calculate_greeks", "params": {"strike_price": 50000, "volatility": 0.8}},
        {"function": "liquidation_price", "params": {"leverage": 5, "entry_price": 50000}},
        {"function": "hedge_position", "params": {"hedge_ratio": 0.5}},
        
        # Spot (3)
        {"function": "spot_momentum_strategy", "params": {"timeframe": "4h"}},
        {"function": "spot_mean_reversion", "params": {"timeframe": "1h"}},
        {"function": "spot_breakout_strategy", "params": {"timeframe": "1h"}},
        
        # Algorithmic (6)
        {"function": "algorithmic_trading", "params": {"strategy_type": "momentum"}},
        {"function": "pairs_trading", "params": {"pair_symbols": "BTC-ETH"}},
        {"function": "statistical_arbitrage", "params": {"universe": "BTC,ETH,SOL"}},
        {"function": "market_making", "params": {"spread_percentage": 0.1}},
        {"function": "scalping_strategy", "params": {"timeframe": "1m"}},
        {"function": "swing_trading", "params": {"timeframe": "1d", "holding_period": 7}},
        
        # Risk & Portfolio (4)
        {"function": "position_management", "params": {"action": "analyze"}},
        {"function": "risk_management", "params": {"analysis_type": "comprehensive"}},
        {"function": "portfolio_optimization", "params": {"rebalance_frequency": "weekly"}},
        {"function": "strategy_performance", "params": {"analysis_period": "30d"}}
    ]
    
    print(f"📊 Testing {len(all_strategy_functions)} strategy functions...")
    
    results = []
    
    for i, strategy_test in enumerate(all_strategy_functions, 1):
        function = strategy_test["function"]
        params = strategy_test["params"]
        
        print(f"\n{i:2d}. Testing: {function}")
        
        payload = {
            "function": function,
            "symbol": "BTC/USDT",
            "parameters": params,
            "simulation_mode": True,  # CRITICAL: Force simulation mode
            "dry_run": True,         # Additional safety flag
            "testing_mode": True     # Explicit testing indicator
        }
        
        try:
            start_time = time.time()
            response = session.post(f"{BASE_URL}/strategies/execute", json=payload)
            execution_time = time.time() - start_time
            
            print(f"     Status: {response.status_code}")
            print(f"     Time: {execution_time:.2f}s")
            
            if response.status_code == 200:
                data = response.json()
                success = data.get("success", False)
                
                if success:
                    execution_result = data.get("execution_result", {})
                    function_name = execution_result.get("function", "unknown")
                    
                    print(f"     ✅ SUCCESS - Function: {function_name}")
                    
                    # Check for real data indicators
                    real_data_indicators = 0
                    if execution_result.get("real_data_sources"):
                        real_data_indicators += 1
                    if any(key for key in execution_result.keys() if "real" in str(key).lower()):
                        real_data_indicators += 1
                    
                    print(f"     📊 Real data indicators: {real_data_indicators}")
                    
                    results.append({
                        "function": function,
                        "success": True,
                        "execution_time": execution_time,
                        "real_data_indicators": real_data_indicators
                    })
                else:
                    error = data.get("error", "Unknown")
                    print(f"     ❌ Execution failed: {error}")
                    
                    results.append({
                        "function": function,
                        "success": False,
                        "error": error
                    })
            else:
                print(f"     ❌ HTTP Error: {response.status_code}")
                error_text = response.text[:100] if response.text else "Unknown"
                
                results.append({
                    "function": function,
                    "success": False,
                    "error": f"HTTP {response.status_code}: {error_text}"
                })
                
        except Exception as e:
            print(f"     ❌ Exception: {e}")
            
            results.append({
                "function": function,
                "success": False,
                "error": str(e)
            })
        
        # Rate limiting
        time.sleep(0.5)
    
    # Final summary
    successful = len([r for r in results if r.get("success", False)])
    with_real_data = len([r for r in results if r.get("success", False) and r.get("real_data_indicators", 0) > 0])
    
    print(f"\n🎯 COMPREHENSIVE TESTING RESULTS")
    print("=" * 70)
    print(f"Total functions tested: {len(results)}")
    print(f"Successful executions: {successful}")
    print(f"Functions with real data: {with_real_data}")
    print(f"Success rate: {successful/len(results)*100:.1f}%")
    print(f"Real data rate: {with_real_data/successful*100:.1f}%" if successful > 0 else "N/A")
    
    # Show working strategies
    print(f"\n✅ WORKING STRATEGIES:")
    working_strategies = [r for r in results if r.get("success", False)]
    for result in working_strategies:
        indicators = result.get("real_data_indicators", 0)
        data_quality = "🎉 REAL DATA" if indicators > 0 else "⚠️ Basic"
        print(f"   - {result['function']}: {data_quality}")
    
    # Show failed strategies
    failed_strategies = [r for r in results if not r.get("success", False)]
    if failed_strategies:
        print(f"\n❌ FAILED STRATEGIES ({len(failed_strategies)}):")
        for result in failed_strategies[:5]:  # Show first 5
            print(f"   - {result['function']}: {result.get('error', 'Unknown')[:50]}")
    
    return results

if __name__ == "__main__":
    test_all_strategies_directly()