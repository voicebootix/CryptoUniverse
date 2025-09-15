#!/usr/bin/env python3
"""
Test Strategy Endpoints

Test all strategy-related endpoints to understand the marketplace structure
"""

import requests
import json

# Configuration
BASE_URL = "https://cryptouniverse.onrender.com/api/v1"
ADMIN_EMAIL = "admin@cryptouniverse.com"
ADMIN_PASSWORD = "AdminPass123!"

def test_all_strategy_endpoints():
    """Test all strategy-related endpoints."""
    
    print("🔍 TESTING ALL STRATEGY ENDPOINTS")
    print("=" * 60)
    
    # Login
    session = requests.Session()
    login_data = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    
    response = session.post(f"{BASE_URL}/auth/login", json=login_data)
    if response.status_code != 200:
        print(f"❌ Login failed")
        return
    
    token = response.json().get("access_token")
    session.headers.update({"Authorization": f"Bearer {token}"})
    print("✅ Authenticated successfully")
    
    # Test all strategy endpoints
    strategy_endpoints = [
        {"method": "GET", "path": "/strategies/marketplace", "name": "Marketplace"},
        {"method": "GET", "path": "/strategies/my-portfolio", "name": "My Portfolio"},
        {"method": "GET", "path": "/strategies/list", "name": "Strategy List"},
        {"method": "GET", "path": "/strategies/available", "name": "Available Strategies"},
        {"method": "POST", "path": "/strategies/purchase", "name": "Purchase Strategy"},
        {"method": "POST", "path": "/strategies/execute", "name": "Execute Strategy"},
        {"method": "GET", "path": "/strategies/ai_risk_management/performance", "name": "Strategy Performance"},
    ]
    
    results = {}
    
    for endpoint in strategy_endpoints:
        method = endpoint["method"]
        path = endpoint["path"]
        name = endpoint["name"]
        
        print(f"\n📊 Testing: {name}")
        print(f"   {method} {path}")
        
        try:
            if method == "GET":
                response = session.get(f"{BASE_URL}{path}")
            else:
                # For POST, provide minimal data
                if "purchase" in path:
                    response = session.post(f"{BASE_URL}{path}?strategy_id=ai_risk_management&subscription_type=monthly")
                elif "execute" in path:
                    payload = {
                        "strategy_id": "ai_risk_management",
                        "symbol": "BTC/USDT",
                        "parameters": {}
                    }
                    response = session.post(f"{BASE_URL}{path}", json=payload)
                else:
                    response = session.post(f"{BASE_URL}{path}", json={})
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ SUCCESS")
                
                # Extract key information
                if isinstance(data, dict):
                    success = data.get("success", "No success field")
                    print(f"   Success: {success}")
                    
                    # Look for strategy-related data
                    for key, value in data.items():
                        if "strateg" in key.lower():
                            if isinstance(value, list):
                                print(f"   {key}: {len(value)} items")
                            else:
                                print(f"   {key}: {value}")
                        elif "count" in key.lower():
                            print(f"   {key}: {value}")
                        elif key in ["total_strategies", "ai_strategies_count", "community_strategies_count"]:
                            print(f"   {key}: {value}")
                
                results[name] = {"success": True, "data": data}
                
            elif response.status_code == 422:
                error_data = response.json()
                print(f"   ⚠️ VALIDATION ERROR")
                print(f"   Details: {error_data.get('detail', 'Unknown')}")
                results[name] = {"success": False, "error": "validation_error", "details": error_data}
                
            else:
                print(f"   ❌ FAILED")
                print(f"   Error: {response.text[:100]}")
                results[name] = {"success": False, "error": response.text[:100]}
                
        except Exception as e:
            print(f"   ❌ EXCEPTION: {e}")
            results[name] = {"success": False, "error": str(e)}
    
    # Summary
    successful_endpoints = sum(1 for r in results.values() if r["success"])
    print(f"\n📊 ENDPOINT TEST SUMMARY:")
    print(f"   Total endpoints tested: {len(results)}")
    print(f"   Successful endpoints: {successful_endpoints}")
    print(f"   Success rate: {successful_endpoints/len(results)*100:.1f}%")
    
    return results

def test_individual_strategy_execution():
    """Test individual strategy execution to see data quality."""
    
    print(f"\n🔧 TESTING INDIVIDUAL STRATEGY EXECUTION")
    print("=" * 60)
    
    # Login
    session = requests.Session()
    login_data = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    
    response = session.post(f"{BASE_URL}/auth/login", json=login_data)
    token = response.json().get("access_token")
    session.headers.update({"Authorization": f"Bearer {token}"})
    
    # Test strategies that admin user has access to
    test_strategies = [
        {
            "strategy_id": "ai_risk_management",
            "name": "AI Risk Management",
            "parameters": {"analysis_type": "comprehensive"}
        },
        {
            "strategy_id": "ai_portfolio_optimization", 
            "name": "AI Portfolio Optimization",
            "parameters": {"rebalance_frequency": "weekly"}
        },
        {
            "strategy_id": "ai_spot_momentum_strategy",
            "name": "AI Spot Momentum",
            "parameters": {"timeframe": "4h", "symbol": "BTC/USDT"}
        }
    ]
    
    execution_results = []
    
    for strategy in test_strategies:
        strategy_id = strategy["strategy_id"]
        name = strategy["name"]
        params = strategy["parameters"]
        
        print(f"\n🎯 Testing: {name}")
        
        # Test via execute endpoint
        payload = {
            "strategy_id": strategy_id,
            "symbol": "BTC/USDT",
            "parameters": params
        }
        
        try:
            start_time = time.time()
            response = session.post(f"{BASE_URL}/strategies/execute", json=payload)
            execution_time = time.time() - start_time
            
            print(f"   Status: {response.status_code}")
            print(f"   Execution time: {execution_time:.2f}s")
            
            if response.status_code == 200:
                data = response.json()
                success = data.get("success", False)
                
                print(f"   Success: {success}")
                
                if success:
                    # Analyze the execution result
                    execution_result = data.get("execution_result", {})
                    strategy_type = data.get("strategy_type", "Unknown")
                    
                    print(f"   Strategy Type: {strategy_type}")
                    print(f"   Execution Result Keys: {list(execution_result.keys())}")
                    
                    # Look for real vs mock data indicators
                    real_data_indicators = []
                    mock_data_indicators = []
                    
                    # Check for real data patterns
                    for key, value in execution_result.items():
                        if isinstance(value, (int, float)) and value > 0:
                            real_data_indicators.append(f"{key}: {value}")
                        elif isinstance(value, dict):
                            for subkey, subvalue in value.items():
                                if isinstance(subvalue, (int, float)) and subvalue > 0:
                                    real_data_indicators.append(f"{key}.{subkey}: {subvalue}")
                    
                    # Check for mock data patterns
                    if "simulation" in str(execution_result).lower():
                        mock_data_indicators.append("Contains 'simulation' keyword")
                    if "mock" in str(execution_result).lower():
                        mock_data_indicators.append("Contains 'mock' keyword")
                    if "placeholder" in str(execution_result).lower():
                        mock_data_indicators.append("Contains 'placeholder' keyword")
                    
                    print(f"   Real data indicators: {len(real_data_indicators)}")
                    for indicator in real_data_indicators[:3]:
                        print(f"      - {indicator}")
                    
                    print(f"   Mock data indicators: {len(mock_data_indicators)}")
                    for indicator in mock_data_indicators:
                        print(f"      - {indicator}")
                    
                    # Determine data quality
                    if len(real_data_indicators) > len(mock_data_indicators):
                        data_quality = "REAL"
                    elif len(mock_data_indicators) > 0:
                        data_quality = "MOCK"
                    else:
                        data_quality = "UNKNOWN"
                    
                    print(f"   📊 Data Quality Assessment: {data_quality}")
                    
                    execution_results.append({
                        "strategy_id": strategy_id,
                        "name": name,
                        "success": True,
                        "execution_time": execution_time,
                        "data_quality": data_quality,
                        "real_indicators": len(real_data_indicators),
                        "mock_indicators": len(mock_data_indicators)
                    })
                else:
                    print(f"   ❌ Execution failed")
                    error = data.get("error", "Unknown error")
                    print(f"   Error: {error}")
                    
                    execution_results.append({
                        "strategy_id": strategy_id,
                        "name": name,
                        "success": False,
                        "error": error
                    })
            else:
                print(f"   ❌ Request failed: {response.text[:100]}")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    # Summary
    successful_executions = sum(1 for r in execution_results if r.get("success", False))
    real_data_strategies = sum(1 for r in execution_results if r.get("data_quality") == "REAL")
    
    print(f"\n📊 EXECUTION TEST SUMMARY:")
    print(f"   Tested strategies: {len(execution_results)}")
    print(f"   Successful executions: {successful_executions}")
    print(f"   Real data strategies: {real_data_strategies}")
    print(f"   Execution success rate: {successful_executions/len(execution_results)*100:.1f}%")
    
    return execution_results

def main():
    print("🔍 COMPREHENSIVE STRATEGY MARKETPLACE ANALYSIS")
    print("=" * 80)
    
    # Test endpoints
    endpoint_results = test_all_strategy_endpoints()
    
    # Test strategy execution
    execution_results = test_individual_strategy_execution()
    
    print(f"\n🎯 FINAL ANALYSIS COMPLETE")
    print("=" * 60)
    
    return {
        "endpoints": endpoint_results,
        "executions": execution_results
    }

if __name__ == "__main__":
    main()