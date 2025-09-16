#!/usr/bin/env python3
"""
Test All Fixes End-to-End

Verify that all implemented fixes are working:
1. Smart Router (Binance.us for market data)
2. SMART_ADAPTIVE parameter (dynamic asset discovery)
3. Exchange priority (Kraken/KuCoin first)
4. Admin user strategies (confirmed provisioned)
"""

import requests
import json
import time

# Configuration
BASE_URL = "https://cryptouniverse.onrender.com/api/v1"
ADMIN_EMAIL = "admin@cryptouniverse.com"
ADMIN_PASSWORD = "AdminPass123!"

def test_all_fixes():
    """Test all implemented fixes."""
    
    print("🚀 TESTING ALL FIXES - END-TO-END VERIFICATION")
    print("=" * 80)
    
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
    
    # Test 1: Market Analysis (should now work with SMART_ADAPTIVE)
    print(f"\n📊 TEST 1: Market Analysis with SMART_ADAPTIVE fix")
    print("=" * 60)
    
    payload = {
        "message": "Analyze the current market conditions and trends",
        "mode": "analysis"
    }
    
    start_time = time.time()
    response = session.post(f"{BASE_URL}/chat/message", json=payload)
    response_time = time.time() - start_time
    
    if response.status_code == 200:
        data = response.json()
        metadata = data.get("metadata", {})
        market_overview = metadata.get("market_overview", {})
        
        print(f"✅ Market Analysis Response:")
        print(f"   Response time: {response_time:.2f}s")
        print(f"   Intent: {data.get('intent')}")
        print(f"   Confidence: {data.get('confidence')}")
        print(f"   Content length: {len(data.get('content', ''))}")
        
        print(f"\n📈 Market Data Quality:")
        print(f"   Sentiment: {market_overview.get('sentiment', 'Unknown')}")
        print(f"   Trend: {market_overview.get('trend', 'Unknown')}")
        print(f"   Market Cap: ${market_overview.get('total_market_cap', 0):,}")
        print(f"   Volume 24h: ${market_overview.get('total_volume_24h', 0):,}")
        print(f"   Available Symbols: {len(market_overview.get('available_symbols', []))}")
        print(f"   BTC Dominance: {market_overview.get('btc_dominance', 0)}%")
        
        # Check if we're getting real data now
        if (market_overview.get('total_market_cap', 0) > 0 or 
            len(market_overview.get('available_symbols', [])) > 0 or
            market_overview.get('sentiment') not in ['Unknown', 'Live']):
            print(f"   🎉 REAL MARKET DATA DETECTED!")
        else:
            print(f"   ⚠️ Still getting placeholder data")
    
    # Test 2: Risk Assessment (should now have real calculations)
    print(f"\n🛡️ TEST 2: Risk Assessment with Real Calculations")
    print("=" * 60)
    
    payload = {
        "message": "What's my portfolio risk level and VaR?",
        "mode": "analysis"
    }
    
    start_time = time.time()
    response = session.post(f"{BASE_URL}/chat/message", json=payload)
    response_time = time.time() - start_time
    
    if response.status_code == 200:
        data = response.json()
        metadata = data.get("metadata", {})
        risk_analysis = metadata.get("risk_analysis", {})
        
        print(f"✅ Risk Assessment Response:")
        print(f"   Response time: {response_time:.2f}s")
        print(f"   Intent: {data.get('intent')}")
        print(f"   Confidence: {data.get('confidence')}")
        
        print(f"\n📊 Risk Metrics Quality:")
        print(f"   Overall Risk: {risk_analysis.get('overall_risk', 'Unknown')}")
        print(f"   VaR 24h: ${risk_analysis.get('var_24h', 0):,.2f}")
        print(f"   VaR 7d: ${risk_analysis.get('var_7d', 0):,.2f}")
        print(f"   Max Drawdown: {risk_analysis.get('max_drawdown', 0):.2f}%")
        print(f"   Sharpe Ratio: {risk_analysis.get('sharpe_ratio', 0):.2f}")
        
        # Check if we're getting real risk calculations now
        if (risk_analysis.get('var_24h', 0) > 0 or 
            risk_analysis.get('sharpe_ratio', 0) != 0 or
            risk_analysis.get('max_drawdown', 0) > 0):
            print(f"   🎉 REAL RISK CALCULATIONS DETECTED!")
        else:
            print(f"   ⚠️ Still getting zero/default values")
    
    # Test 3: Opportunity Discovery (should now work with strategies)
    print(f"\n🔍 TEST 3: Opportunity Discovery with Active Strategies")
    print("=" * 60)
    
    payload = {
        "message": "Find me the best investment opportunities using all my strategies",
        "mode": "analysis"
    }
    
    start_time = time.time()
    response = session.post(f"{BASE_URL}/chat/message", json=payload)
    response_time = time.time() - start_time
    
    if response.status_code == 200:
        data = response.json()
        metadata = data.get("metadata", {})
        
        print(f"✅ Opportunity Discovery Response:")
        print(f"   Response time: {response_time:.2f}s")
        print(f"   Intent: {data.get('intent')}")
        print(f"   Confidence: {data.get('confidence')}")
        print(f"   Opportunities found: {metadata.get('opportunities_count', 0)}")
        print(f"   Service used: {metadata.get('service_used', 'Unknown')}")
        
        # Check AI analysis
        ai_analysis = metadata.get("ai_analysis", {})
        if ai_analysis:
            opportunity_analysis = ai_analysis.get("opportunity_analysis", {})
            print(f"   AI Consensus Score: {opportunity_analysis.get('consensus_score', 0):.1f}%")
            print(f"   AI Recommendation: {opportunity_analysis.get('recommendation', 'Unknown')}")
            print(f"   Models Used: {opportunity_analysis.get('cost_summary', {}).get('models_used', 0)}")
            print(f"   Total Cost: ${opportunity_analysis.get('cost_summary', {}).get('total_cost', 0):.4f}")
        
        if metadata.get('opportunities_count', 0) > 0:
            print(f"   🎉 OPPORTUNITIES FOUND!")
        else:
            print(f"   ⚠️ Still no opportunities - investigating further...")
            
            # Check the content for clues
            content = data.get("content", "")
            if "no tradeable assets found" in content.lower():
                print(f"   Issue: Asset discovery failing")
            elif "no strategies" in content.lower():
                print(f"   Issue: Strategy provisioning failing")
            elif "analysis" in content.lower():
                print(f"   Issue: Analysis completing but finding no opportunities")
    
    # Test 4: Portfolio Analysis (should still work)
    print(f"\n💰 TEST 4: Portfolio Analysis (Baseline Check)")
    print("=" * 60)
    
    payload = {
        "message": "Show me my complete portfolio breakdown and performance",
        "mode": "analysis"
    }
    
    start_time = time.time()
    response = session.post(f"{BASE_URL}/chat/message", json=payload)
    response_time = time.time() - start_time
    
    if response.status_code == 200:
        data = response.json()
        metadata = data.get("metadata", {})
        portfolio_summary = metadata.get("portfolio_summary", {})
        
        print(f"✅ Portfolio Analysis Response:")
        print(f"   Response time: {response_time:.2f}s")
        print(f"   Intent: {data.get('intent')}")
        print(f"   Total Value: ${portfolio_summary.get('total_value', 0):,.2f}")
        print(f"   Positions: {len(portfolio_summary.get('positions', []))}")
        print(f"   Exchanges: {len(portfolio_summary.get('exchanges', []))}")
        print(f"   Data Source: {portfolio_summary.get('data_source', 'Unknown')}")
        
        if portfolio_summary.get('total_value', 0) > 0:
            print(f"   ✅ Portfolio data still working correctly")
        else:
            print(f"   ❌ Portfolio data issue")
    
    return True

if __name__ == "__main__":
    test_all_fixes()