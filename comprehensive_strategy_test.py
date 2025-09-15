#!/usr/bin/env python3
"""
Comprehensive Strategy Test

Test all available strategy functions to determine data quality
"""

import requests
import json
import time

# Configuration
BASE_URL = "https://cryptouniverse.onrender.com/api/v1"
ADMIN_EMAIL = "admin@cryptouniverse.com"
ADMIN_PASSWORD = "AdminPass123!"

def test_all_available_functions():
    """Test all available strategy functions."""
    
    print("🔬 COMPREHENSIVE STRATEGY FUNCTION TESTING")
    print("=" * 70)
    
    # Login
    session = requests.Session()
    login_data = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    
    response = session.post(f"{BASE_URL}/auth/login", json=login_data)
    token = response.json().get("access_token")
    session.headers.update({"Authorization": f"Bearer {token}"})
    print("✅ Authenticated successfully")
    
    # Get available strategies to understand what functions exist
    response = session.get(f"{BASE_URL}/strategies/available")
    available_strategies = response.json().get("available_strategies", {})
    
    print(f"\n📊 Available strategy functions: {len(available_strategies)}")
    
    # Test each available function
    test_results = []
    
    for function_name, strategy_info in available_strategies.items():
        name = strategy_info.get("name", "Unknown")
        category = strategy_info.get("category", "unknown")
        risk_level = strategy_info.get("risk_level", "unknown")
        min_capital = strategy_info.get("min_capital", 0)
        
        print(f"\n🎯 Testing Function: {function_name}")
        print(f"   Name: {name}")
        print(f"   Category: {category}")
        print(f"   Risk: {risk_level}")
        print(f"   Min Capital: ${min_capital:,}")
        
        # Prepare test payload
        payload = {
            "function": function_name,
            "symbol": "BTC/USDT",
            "parameters": {},
            "simulation_mode": True
        }
        
        # Add function-specific parameters
        if function_name == "futures_trade":
            payload["strategy_type"] = "long_futures"
            payload["parameters"] = {"leverage": 3, "position_size": 1000}
        elif function_name == "options_trade":
            payload["strategy_type"] = "call_option"
            payload["parameters"] = {"strike_price": 50000, "expiry": "2024-01-01"}
        elif function_name == "pairs_trading":
            payload["parameters"] = {"pair_symbols": "BTC-ETH"}
        elif function_name == "statistical_arbitrage":
            payload["parameters"] = {"universe": "BTC,ETH,SOL"}
        elif "spot" in function_name:
            payload["parameters"] = {"timeframe": "4h"}
        
        try:
            start_time = time.time()
            response = session.post(f"{BASE_URL}/strategies/execute", json=payload)
            execution_time = time.time() - start_time
            
            print(f"   Status: {response.status_code}")
            print(f"   Time: {execution_time:.2f}s")
            
            if response.status_code == 200:
                data = response.json()
                success = data.get("success", False)
                
                if success:
                    execution_result = data.get("execution_result", {})
                    
                    # Analyze data depth and quality
                    total_fields = 0
                    non_empty_fields = 0
                    numerical_fields = 0
                    zero_values = 0
                    
                    def analyze_data_structure(obj, depth=0):
                        nonlocal total_fields, non_empty_fields, numerical_fields, zero_values
                        
                        if depth > 3:  # Prevent infinite recursion
                            return
                            
                        if isinstance(obj, dict):
                            for key, value in obj.items():
                                total_fields += 1
                                
                                if value is not None and value != "" and value != {}:
                                    non_empty_fields += 1
                                
                                if isinstance(value, (int, float)):
                                    numerical_fields += 1
                                    if value == 0:
                                        zero_values += 1
                                elif isinstance(value, (dict, list)):
                                    analyze_data_structure(value, depth + 1)
                        elif isinstance(obj, list):
                            for item in obj:
                                analyze_data_structure(item, depth + 1)
                    
                    analyze_data_structure(execution_result)
                    
                    # Calculate quality metrics
                    completeness = (non_empty_fields / total_fields * 100) if total_fields > 0 else 0
                    zero_percentage = (zero_values / numerical_fields * 100) if numerical_fields > 0 else 0
                    
                    print(f"   📊 Data Analysis:")
                    print(f"      Total fields: {total_fields}")
                    print(f"      Non-empty fields: {non_empty_fields}")
                    print(f"      Completeness: {completeness:.1f}%")
                    print(f"      Numerical fields: {numerical_fields}")
                    print(f"      Zero values: {zero_values} ({zero_percentage:.1f}%)")
                    
                    # Determine data quality
                    if completeness > 70 and zero_percentage < 30:
                        quality = "HIGH_QUALITY"
                    elif completeness > 50 and zero_percentage < 60:
                        quality = "MEDIUM_QUALITY"
                    else:
                        quality = "LOW_QUALITY"
                    
                    print(f"   🎯 Quality Assessment: {quality}")
                    
                    # Look for specific real data indicators
                    real_indicators = []
                    if "portfolio_risk_metrics" in execution_result:
                        risk_metrics = execution_result["portfolio_risk_metrics"]
                        if risk_metrics.get("portfolio_var_1d_95", 0) > 0:
                            real_indicators.append("Real VaR calculations")
                    
                    if "signal" in execution_result:
                        signal = execution_result["signal"]
                        if signal.get("strength", 0) > 0:
                            real_indicators.append("Real trading signals")
                    
                    if real_indicators:
                        print(f"   ✅ Real data detected:")
                        for indicator in real_indicators:
                            print(f"      - {indicator}")
                    
                    test_results.append({
                        "function": function_name,
                        "name": name,
                        "category": category,
                        "success": True,
                        "execution_time": execution_time,
                        "data_quality": quality,
                        "completeness": completeness,
                        "zero_percentage": zero_percentage,
                        "real_indicators": real_indicators
                    })
                    
                else:
                    error = data.get("error", "Unknown")
                    print(f"   ❌ Execution failed: {error}")
                    
                    test_results.append({
                        "function": function_name,
                        "name": name,
                        "category": category,
                        "success": False,
                        "error": error
                    })
            else:
                print(f"   ❌ HTTP Error: {response.status_code}")
                error_text = response.text[:100] if response.text else "Unknown error"
                
                test_results.append({
                    "function": function_name,
                    "name": name,
                    "category": category,
                    "success": False,
                    "error": f"HTTP {response.status_code}: {error_text}"
                })
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")
            
            test_results.append({
                "function": function_name,
                "name": name,
                "category": category,
                "success": False,
                "error": str(e)
            })
    
    # Final summary
    print(f"\n🎯 COMPREHENSIVE ANALYSIS SUMMARY")
    print("=" * 70)
    
    total_tested = len(test_results)
    successful = len([r for r in test_results if r.get("success", False)])
    high_quality = len([r for r in test_results if r.get("data_quality") == "HIGH_QUALITY"])
    medium_quality = len([r for r in test_results if r.get("data_quality") == "MEDIUM_QUALITY"])
    low_quality = len([r for r in test_results if r.get("data_quality") == "LOW_QUALITY"])
    
    print(f"📊 EXECUTION RESULTS:")
    print(f"   Total functions tested: {total_tested}")
    print(f"   Successful executions: {successful}")
    print(f"   Success rate: {successful/total_tested*100:.1f}%")
    
    print(f"\n📊 DATA QUALITY RESULTS:")
    print(f"   High quality data: {high_quality}")
    print(f"   Medium quality data: {medium_quality}")
    print(f"   Low quality data: {low_quality}")
    
    if successful > 0:
        print(f"   Data quality rate: {(high_quality + medium_quality)/successful*100:.1f}%")
    
    print(f"\n📈 BY CATEGORY:")
    categories = {}
    for result in test_results:
        cat = result.get("category", "unknown")
        if cat not in categories:
            categories[cat] = {"total": 0, "successful": 0, "high_quality": 0}
        categories[cat]["total"] += 1
        if result.get("success", False):
            categories[cat]["successful"] += 1
            if result.get("data_quality") == "HIGH_QUALITY":
                categories[cat]["high_quality"] += 1
    
    for category, stats in categories.items():
        print(f"   {category.capitalize()}:")
        print(f"      Total: {stats['total']}")
        print(f"      Working: {stats['successful']}")
        print(f"      High Quality: {stats['high_quality']}")
    
    return test_results

if __name__ == "__main__":
    test_all_available_functions()