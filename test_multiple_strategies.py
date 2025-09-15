#!/usr/bin/env python3
"""
Test Multiple Strategies for Data Quality Analysis

Test different strategies to analyze if they generate real or mock data
"""

import requests
import json
import time

# Configuration
BASE_URL = "https://cryptouniverse.onrender.com/api/v1"
ADMIN_EMAIL = "admin@cryptouniverse.com"
ADMIN_PASSWORD = "AdminPass123!"

def test_strategy_data_quality():
    """Test multiple strategies to analyze data quality."""
    
    print("🔬 STRATEGY DATA QUALITY ANALYSIS")
    print("=" * 70)
    
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
    
    # Test different strategy functions
    strategy_tests = [
        {
            "function": "risk_management",
            "name": "Risk Management",
            "parameters": {"analysis_type": "comprehensive"},
            "expect_real_data": ["portfolio_risk_metrics", "individual_position_risks"]
        },
        {
            "function": "portfolio_optimization",
            "name": "Portfolio Optimization", 
            "parameters": {"rebalance_frequency": "weekly"},
            "expect_real_data": ["rebalancing_recommendations", "current_allocation"]
        },
        {
            "function": "spot_momentum_strategy",
            "name": "Spot Momentum Strategy",
            "parameters": {"timeframe": "4h"},
            "expect_real_data": ["signal", "indicators", "technical_analysis"]
        },
        {
            "function": "spot_mean_reversion",
            "name": "Spot Mean Reversion",
            "parameters": {"timeframe": "1h"},
            "expect_real_data": ["signals", "statistical_analysis"]
        },
        {
            "function": "market_making",
            "name": "Market Making",
            "parameters": {"spread_percentage": 0.1},
            "expect_real_data": ["spread_analysis", "liquidity_metrics"]
        }
    ]
    
    strategy_results = []
    
    for test in strategy_tests:
        function = test["function"]
        name = test["name"]
        parameters = test["parameters"]
        expected_data = test["expect_real_data"]
        
        print(f"\n🎯 Testing: {name}")
        print(f"   Function: {function}")
        
        payload = {
            "function": function,
            "symbol": "BTC/USDT",
            "parameters": parameters,
            "simulation_mode": True
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
                    execution_result = data.get("execution_result", {})
                    
                    # Analyze data quality
                    real_data_score = 0
                    mock_data_score = 0
                    data_analysis = []
                    
                    # Check for expected real data fields
                    for expected_field in expected_data:
                        if expected_field in execution_result:
                            field_data = execution_result[expected_field]
                            if field_data and field_data != {}:
                                real_data_score += 1
                                data_analysis.append(f"✅ {expected_field}: Present")
                            else:
                                data_analysis.append(f"⚠️ {expected_field}: Empty")
                        else:
                            data_analysis.append(f"❌ {expected_field}: Missing")
                    
                    # Check for mock data indicators
                    result_str = json.dumps(execution_result)
                    mock_indicators = [
                        "simulation", "mock", "placeholder", "template", 
                        "example", "demo", "test", "fake"
                    ]
                    
                    for indicator in mock_indicators:
                        if indicator in result_str.lower():
                            mock_data_score += 1
                            data_analysis.append(f"⚠️ Mock indicator: '{indicator}' found")
                    
                    # Check for real numerical data
                    numerical_fields = 0
                    zero_fields = 0
                    
                    def count_numerical_data(obj, prefix=""):
                        nonlocal numerical_fields, zero_fields
                        if isinstance(obj, dict):
                            for k, v in obj.items():
                                if isinstance(v, (int, float)):
                                    numerical_fields += 1
                                    if v == 0:
                                        zero_fields += 1
                                elif isinstance(v, dict):
                                    count_numerical_data(v, f"{prefix}.{k}")
                    
                    count_numerical_data(execution_result)
                    
                    # Calculate data quality score
                    if numerical_fields > 0:
                        zero_percentage = (zero_fields / numerical_fields) * 100
                        data_analysis.append(f"📊 Numerical fields: {numerical_fields}, Zeros: {zero_fields} ({zero_percentage:.1f}%)")
                    
                    # Determine overall data quality
                    if real_data_score > 0 and mock_data_score == 0 and zero_percentage < 50:
                        data_quality = "REAL"
                    elif mock_data_score > 0 or zero_percentage > 80:
                        data_quality = "MOCK"
                    else:
                        data_quality = "MIXED"
                    
                    print(f"   📊 Data Quality: {data_quality}")
                    print(f"   Real data score: {real_data_score}")
                    print(f"   Mock data score: {mock_data_score}")
                    
                    for analysis in data_analysis[:5]:  # Show first 5 analysis points
                        print(f"      {analysis}")
                    
                    strategy_results.append({
                        "function": function,
                        "name": name,
                        "success": True,
                        "execution_time": execution_time,
                        "data_quality": data_quality,
                        "real_score": real_data_score,
                        "mock_score": mock_data_score,
                        "zero_percentage": zero_percentage if numerical_fields > 0 else 0
                    })
                else:
                    error = data.get("error", "Unknown")
                    print(f"   ❌ Execution failed: {error}")
                    
                    strategy_results.append({
                        "function": function,
                        "name": name,
                        "success": False,
                        "error": error
                    })
            else:
                print(f"   ❌ Request failed: {response.status_code}")
                print(f"   Error: {response.text[:100]}")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
    
    # Summary analysis
    print(f"\n📊 DATA QUALITY SUMMARY")
    print("=" * 60)
    
    successful_tests = [r for r in strategy_results if r.get("success", False)]
    real_data_strategies = [r for r in successful_tests if r.get("data_quality") == "REAL"]
    mock_data_strategies = [r for r in successful_tests if r.get("data_quality") == "MOCK"]
    mixed_data_strategies = [r for r in successful_tests if r.get("data_quality") == "MIXED"]
    
    print(f"Total strategies tested: {len(strategy_results)}")
    print(f"Successful executions: {len(successful_tests)}")
    print(f"Real data strategies: {len(real_data_strategies)}")
    print(f"Mock data strategies: {len(mock_data_strategies)}")
    print(f"Mixed data strategies: {len(mixed_data_strategies)}")
    
    if successful_tests:
        avg_execution_time = sum(r["execution_time"] for r in successful_tests) / len(successful_tests)
        print(f"Average execution time: {avg_execution_time:.2f}s")
    
    print(f"\n📈 DATA QUALITY BREAKDOWN:")
    for result in successful_tests:
        quality = result["data_quality"]
        emoji = "✅" if quality == "REAL" else "⚠️" if quality == "MIXED" else "❌"
        print(f"   {emoji} {result['name']}: {quality}")
    
    return strategy_results

if __name__ == "__main__":
    test_strategy_data_quality()