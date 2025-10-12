#!/usr/bin/env python3
"""
Test opportunity discovery on live deployment

Required Environment Variables:
- TEST_ADMIN_EMAIL: Admin email for testing
- TEST_ADMIN_PASSWORD: Admin password for testing

Usage:
    export TEST_ADMIN_EMAIL="admin@cryptouniverse.com"
    export TEST_ADMIN_PASSWORD="AdminPass123!"
    python3 test_opportunity_discovery_live.py
"""

import os
import requests
import json
import time
import sys
import logging
import traceback

def test_opportunity_discovery_live():
    """Test opportunity discovery on live deployment"""
    
    # Check for required environment variables
    admin_email = os.environ.get("TEST_ADMIN_EMAIL")
    admin_password = os.environ.get("TEST_ADMIN_PASSWORD")
    
    if not admin_email or not admin_password:
        print("❌ Missing required environment variables!")
        print("Please set the following environment variables:")
        print("  export TEST_ADMIN_EMAIL='admin@cryptouniverse.com'")
        print("  export TEST_ADMIN_PASSWORD='AdminPass123!'")
        sys.exit(1)
    
    base_url = "https://cryptouniverse.onrender.com/api/v1"
    
    # Login
    print("🔐 Logging in...")
    login_data = {
        "email": admin_email, 
        "password": admin_password
    }
    
    response = requests.post(f"{base_url}/auth/login", json=login_data, timeout=30)
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        print(f"Response: {response.text}")
        return
    
    token = response.json().get("access_token")
    user_id = response.json().get("user_id")
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"✅ Login successful - User ID: {user_id}")
    
    # Test 1: Check user's strategy portfolio
    print(f"\n1️⃣ Testing user strategy portfolio...")
    
    try:
        portfolio_response = requests.get(f"{base_url}/unified-strategies/portfolio", 
                                        headers=headers, 
                                        timeout=30)
        
        print(f"   Status: {portfolio_response.status_code}")
        
        if portfolio_response.status_code == 200:
            portfolio_data = portfolio_response.json()
            print(f"   Success: {portfolio_data.get('success')}")
            print(f"   Active strategies: {len(portfolio_data.get('active_strategies', []))}")
            print(f"   Total strategies: {portfolio_data.get('total_strategies', 0)}")
            
            if portfolio_data.get('active_strategies'):
                print(f"   Strategy names: {[s.get('name') for s in portfolio_data.get('active_strategies', [])[:5]]}")
        else:
            print(f"   Error: {portfolio_response.text[:200]}")
            
    except requests.exceptions.Timeout:
        print(f"   ❌ Request timeout - portfolio endpoint took too long to respond")
    except requests.exceptions.ConnectionError as e:
        print(f"   ❌ Connection error - could not reach portfolio endpoint: {e}")
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Request failed: {e}")
    except (ValueError, json.JSONDecodeError) as e:
        print(f"   ❌ Response parsing error: {e}")
        print(f"   Raw response: {portfolio_response.text[:200] if 'portfolio_response' in locals() else 'N/A'}")
    except Exception as e:
        print(f"   ❌ Unexpected error in portfolio test: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        raise
    
    # Test 2: Test opportunity discovery endpoint directly
    print(f"\n2️⃣ Testing opportunity discovery endpoint...")
    
    try:
        discover_data = {
            "force_refresh": True,
            "include_strategy_recommendations": True
        }
        
        start_time = time.time()
        discover_response = requests.post(f"{base_url}/opportunities/discover", 
                                        headers=headers, 
                                        json=discover_data,
                                        timeout=120)
        response_time = time.time() - start_time
        
        print(f"   Status: {discover_response.status_code}")
        print(f"   Response time: {response_time:.2f}s")
        
        if discover_response.status_code == 200:
            discover_result = discover_response.json()
            print(f"   Success: {discover_result.get('success')}")
            print(f"   Total opportunities: {discover_result.get('total_opportunities', 0)}")
            print(f"   Execution time: {discover_result.get('execution_time_ms', 0):.2f}ms")
            
            if discover_result.get('error'):
                print(f"   Error: {discover_result['error']}")
            
            # Check user profile
            user_profile = discover_result.get('user_profile', {})
            if user_profile:
                print(f"   User profile:")
                print(f"      Active strategies: {user_profile.get('active_strategies', 0)}")
                print(f"      User tier: {user_profile.get('user_tier', 'Unknown')}")
            
            # Check opportunities
            opportunities = discover_result.get('opportunities', [])
            if opportunities:
                print(f"   ✅ FOUND {len(opportunities)} OPPORTUNITIES!")
                for i, opp in enumerate(opportunities[:5]):
                    print(f"      {i+1}. {opp.get('symbol')} on {opp.get('exchange')}")
                    print(f"         Strategy: {opp.get('strategy_name')}")
                    print(f"         Profit: ${opp.get('profit_potential_usd', 0):.2f}")
                    print(f"         Confidence: {opp.get('confidence_score', 0):.1f}%")
                    print(f"         Risk: {opp.get('risk_level')}")
            else:
                print(f"   ❌ No opportunities found")
                
                # Check strategy performance details
                strategy_performance = discover_result.get('strategy_performance', {})
                if strategy_performance:
                    print(f"   Strategy scan results:")
                    for strategy_id, perf in strategy_performance.items():
                        opportunities_found = perf.get('opportunities_found', 0)
                        success = perf.get('success', False)
                        error = perf.get('error', 'None')
                        print(f"      {strategy_id}: {opportunities_found} opportunities, success={success}, error={error}")
        else:
            print(f"   Error: {discover_response.text}")
    except requests.exceptions.Timeout:
        print(f"   ❌ Request timeout - opportunity discovery endpoint took too long to respond")
    except requests.exceptions.ConnectionError as e:
        print(f"   ❌ Connection error - could not reach opportunity discovery endpoint: {e}")
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Request failed: {e}")
    except (ValueError, json.JSONDecodeError) as e:
        print(f"   ❌ Response parsing error: {e}")
        print(f"   Raw response: {discover_response.text[:200] if 'discover_response' in locals() else 'N/A'}")
    except Exception as e:
        print(f"   ❌ Unexpected error in opportunity discovery test: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        raise
    
    # Test 3: Test chat opportunity discovery
    print(f"\n3️⃣ Testing chat opportunity discovery...")
    
    try:
        message_data = {
            "message": "Find me trading opportunities",
            "mode": "trading"
        }
        
        start_time = time.time()
        chat_response = requests.post(f"{base_url}/chat/message", 
                                     json=message_data, 
                                     headers=headers, 
                                     timeout=120)
        response_time = time.time() - start_time
        
        print(f"   Status: {chat_response.status_code}")
        print(f"   Response time: {response_time:.2f}s")
        
        if chat_response.status_code == 200:
            chat_data = chat_response.json()
            print(f"   Success: {chat_data.get('success')}")
            print(f"   Intent: {chat_data.get('intent')}")
            
            content = chat_data.get('content', '')
            print(f"   Content preview: {content[:300]}...")
            
            # Check if response looks like a placeholder
            if "rebalancing plan" in content.lower() and "portfolio optimization" in content.lower():
                print(f"   ✅ Response looks like real opportunity analysis")
            elif "scanning your active strategies" in content.lower() or "opportunity scan started" in content.lower():
                print(f"   ⚠️  Response looks like placeholder/loading message")
            else:
                print(f"   ❓ Response format unclear")
            
            metadata = chat_data.get('metadata', {})
            opportunities = metadata.get('opportunities', [])
            print(f"   Chat opportunities: {len(opportunities)}")
            
            if opportunities:
                print(f"   ✅ CHAT FOUND OPPORTUNITIES!")
                for i, opp in enumerate(opportunities[:3]):
                    print(f"      {i+1}. {opp.get('symbol', 'Unknown')}: {opp.get('confidence', 0)}% confidence")
            else:
                print(f"   ❌ Chat found no opportunities")
        else:
            print(f"   Error: {chat_response.text}")
    except requests.exceptions.Timeout:
        print(f"   ❌ Request timeout - chat endpoint took too long to respond")
    except requests.exceptions.ConnectionError as e:
        print(f"   ❌ Connection error - could not reach chat endpoint: {e}")
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Request failed: {e}")
    except (ValueError, json.JSONDecodeError) as e:
        print(f"   ❌ Response parsing error: {e}")
        print(f"   Raw response: {chat_response.text[:200] if 'chat_response' in locals() else 'N/A'}")
    except Exception as e:
        print(f"   ❌ Unexpected error in chat test: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        raise
    
    # Test 4: Check admin strategy access
    print(f"\n4️⃣ Testing admin strategy access...")
    
    try:
        admin_status_response = requests.get(f"{base_url}/admin-strategy-access/admin-portfolio-status", 
                                           headers=headers, 
                                           timeout=30)
        
        print(f"   Status: {admin_status_response.status_code}")
        
        if admin_status_response.status_code == 200:
            admin_data = admin_status_response.json()
            print(f"   Success: {admin_data.get('success')}")
            print(f"   Has full access: {admin_data.get('has_full_access', False)}")
            print(f"   Available strategies: {admin_data.get('available_strategies', 0)}")
            print(f"   Active strategies: {admin_data.get('active_strategies', 0)}")
        else:
            print(f"   Error: {admin_status_response.text}")
    except requests.exceptions.Timeout:
        print(f"   ❌ Request timeout - admin status endpoint took too long to respond")
    except requests.exceptions.ConnectionError as e:
        print(f"   ❌ Connection error - could not reach admin status endpoint: {e}")
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Request failed: {e}")
    except (ValueError, json.JSONDecodeError) as e:
        print(f"   ❌ Response parsing error: {e}")
        print(f"   Raw response: {admin_status_response.text[:200] if 'admin_status_response' in locals() else 'N/A'}")
    except Exception as e:
        print(f"   ❌ Unexpected error in admin status test: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        raise
    
    print(f"\n{'='*60}")
    print("📊 ANALYSIS SUMMARY:")
    print("1. If portfolio shows active strategies > 0, user has strategies")
    print("2. If opportunity discovery finds opportunities > 0, system is working")
    print("3. If chat response contains real analysis (not placeholder), AI is working")
    print("4. If admin has full access, all 14 strategies should be available")

if __name__ == "__main__":
    test_opportunity_discovery_live()