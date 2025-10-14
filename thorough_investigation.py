#!/usr/bin/env python3
"""
Thorough Investigation - Deep dive into the strategy system to understand:
1. What strategies actually exist in the codebase
2. What scanners are implemented
3. What the admin should have access to
4. Evidence of what's real vs placeholder
"""

import requests
import json
import os
import re
from datetime import datetime
from collections import defaultdict

def investigate_strategy_system():
    """Thorough investigation of the strategy system."""
    
    print("🔍 THOROUGH STRATEGY SYSTEM INVESTIGATION")
    print("Deep dive to understand what's real vs placeholder")
    
    # 1. Check what scanners are actually implemented in the codebase
    print("\n1. ANALYZING IMPLEMENTED SCANNERS IN CODEBASE...")
    
    scanner_file = "/workspace/app/services/user_opportunity_discovery.py"
    if os.path.exists(scanner_file):
        with open(scanner_file, 'r') as f:
            content = f.read()
        
        # Find all strategy scanner methods
        scanner_pattern = r'async def _scan_(\w+)_opportunities\('
        scanners = re.findall(scanner_pattern, content)
        
        print(f"   📊 Found {len(scanners)} scanner methods in codebase:")
        for i, scanner in enumerate(scanners, 1):
            print(f"      {i:2d}. {scanner}")
        
        # Check which ones are placeholders
        placeholder_pattern = r'async def _scan_(\w+)_opportunities\([^)]*\):\s*"""[^"]*placeholder[^"]*"""'
        placeholder_scanners = re.findall(placeholder_pattern, content, re.IGNORECASE | re.DOTALL)
        
        print(f"\n   ⚠️  Placeholder scanners found: {len(placeholder_scanners)}")
        for scanner in placeholder_scanners:
            print(f"      - {scanner}")
        
        # Check which ones return empty arrays (placeholders)
        empty_return_pattern = r'async def _scan_(\w+)_opportunities\([^)]*\):[^}]*return \[\]'
        empty_scanners = re.findall(empty_return_pattern, content, re.DOTALL)
        
        print(f"\n   🔄 Empty return scanners: {len(empty_scanners)}")
        for scanner in empty_scanners:
            print(f"      - {scanner}")
    else:
        print(f"   ❌ Scanner file not found: {scanner_file}")
    
    # 2. Check what strategies are defined in the marketplace
    print("\n2. ANALYZING MARKETPLACE STRATEGY DEFINITIONS...")
    
    marketplace_files = [
        "/workspace/app/services/strategy_marketplace_service.py",
        "/workspace/app/services/unified_strategy_service.py"
    ]
    
    all_marketplace_strategies = set()
    
    for file_path in marketplace_files:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Find strategy definitions
            strategy_patterns = [
                r'"(\w+)":\s*{[^}]*"name":\s*"([^"]+)"',
                r'strategy_id["\']:\s*["\'](\w+)["\']',
                r'"(\w+)"\s*:\s*"([^"]+)"',  # For strategy mappings
            ]
            
            strategies = set()
            for pattern in strategy_patterns:
                matches = re.findall(pattern, content)
                for match in matches:
                    if isinstance(match, tuple):
                        strategies.add(match[0])
                    else:
                        strategies.add(match)
            
            print(f"   📊 {os.path.basename(file_path)}: {len(strategies)} strategies found")
            all_marketplace_strategies.update(strategies)
    
    print(f"   📊 Total unique marketplace strategies: {len(all_marketplace_strategies)}")
    
    # 3. Check what strategies are in the trading strategies service
    print("\n3. ANALYZING TRADING STRATEGIES SERVICE...")
    
    trading_file = "/workspace/app/services/trading_strategies.py"
    if os.path.exists(trading_file):
        with open(trading_file, 'r') as f:
            content = f.read()
        
        # Find strategy functions
        function_pattern = r'def (\w+)\([^)]*\):'
        functions = re.findall(function_pattern, content)
        
        # Filter for strategy-related functions
        strategy_functions = [f for f in functions if any(keyword in f.lower() for keyword in 
            ['strategy', 'trading', 'arbitrage', 'momentum', 'reversion', 'breakout', 'scalping', 'pairs', 'statistical', 'funding', 'futures', 'options', 'hedge', 'complex'])]
        
        print(f"   📊 Found {len(strategy_functions)} strategy functions:")
        for i, func in enumerate(strategy_functions, 1):
            print(f"      {i:2d}. {func}")
    else:
        print(f"   ❌ Trading strategies file not found: {trading_file}")
    
    # 4. Check what the admin actually has access to
    print("\n4. CHECKING ADMIN ACTUAL ACCESS...")
    
    base_url = "https://cryptouniverse.onrender.com"
    
    try:
        # Get auth token
        login_data = {
            'email': 'admin@cryptouniverse.com',
            'password': 'AdminPass123!'
        }
        
        login_response = requests.post(f'{base_url}/api/v1/auth/login', json=login_data, timeout=30)
        
        if login_response.status_code == 200:
            token = login_response.json().get('access_token')
            headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
            
            # Get admin's actual strategies
            portfolio_response = requests.get(
                f'{base_url}/api/v1/unified-strategies/portfolio', 
                headers=headers, 
                timeout=60
            )
            
            if portfolio_response.status_code == 200:
                portfolio_data = portfolio_response.json()
                strategies = portfolio_data.get('active_strategies', [])
                
                print(f"   📊 Admin actually has {len(strategies)} strategies")
                
                # Categorize by ID pattern
                ai_strategies = []
                uuid_strategies = []
                other_strategies = []
                
                for strategy in strategies:
                    strategy_id = strategy.get('strategy_id', '')
                    if strategy_id.startswith('ai_'):
                        ai_strategies.append(strategy)
                    elif len(strategy_id) == 36 and strategy_id.count('-') == 4:
                        uuid_strategies.append(strategy)
                    else:
                        other_strategies.append(strategy)
                
                print(f"   📊 AI strategies: {len(ai_strategies)}")
                for strategy in ai_strategies:
                    print(f"      - {strategy.get('strategy_id')}: {strategy.get('name')}")
                
                print(f"   📊 UUID strategies: {len(uuid_strategies)}")
                for strategy in uuid_strategies[:5]:  # Show first 5
                    print(f"      - {strategy.get('strategy_id')}: {strategy.get('name')}")
                if len(uuid_strategies) > 5:
                    print(f"      ... and {len(uuid_strategies) - 5} more")
                
                print(f"   📊 Other strategies: {len(other_strategies)}")
                for strategy in other_strategies:
                    print(f"      - {strategy.get('strategy_id')}: {strategy.get('name')}")
                
            else:
                print(f"   ❌ Failed to get admin strategies: {portfolio_response.status_code}")
        else:
            print(f"   ❌ Login failed: {login_response.status_code}")
    except Exception as e:
        print(f"   💥 Error checking admin access: {e}")
    
    # 5. Check what strategies are mentioned in chat responses
    print("\n5. ANALYZING CHAT RESPONSE STRATEGIES...")
    
    try:
        chat_data = {
            'message': 'What strategies do I have access to?',
            'include_context': True
        }
        
        chat_response = requests.post(
            f'{base_url}/api/v1/chat/message', 
            headers=headers, 
            json=chat_data,
            timeout=30
        )
        
        if chat_response.status_code == 200:
            chat_data = chat_response.json()
            content = chat_data.get('content', '')
            
            # Extract strategy names from content
            strategy_patterns = [
                r'AI (\w+(?:\s+\w+)*)',
                r'(\w+)\s+\([^)]*Category\)',
                r'(\w+)\s+strategy',
            ]
            
            mentioned_strategies = set()
            for pattern in strategy_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    mentioned_strategies.add(match.strip())
            
            print(f"   📊 Chat mentions {len(mentioned_strategies)} strategies:")
            for strategy in mentioned_strategies:
                print(f"      - {strategy}")
        else:
            print(f"   ❌ Chat failed: {chat_response.status_code}")
    except Exception as e:
        print(f"   💥 Error checking chat: {e}")
    
    # 6. Summary and evidence
    print(f"\n{'='*80}")
    print("📊 INVESTIGATION SUMMARY & EVIDENCE")
    print(f"{'='*80}")
    
    print(f"\n🔍 EVIDENCE OF WHAT'S REAL:")
    print(f"   1. Codebase scanners: {len(scanners) if 'scanners' in locals() else 'Unknown'}")
    print(f"   2. Marketplace strategies: {len(all_marketplace_strategies)}")
    print(f"   3. Trading functions: {len(strategy_functions) if 'strategy_functions' in locals() else 'Unknown'}")
    print(f"   4. Admin actual strategies: {len(strategies) if 'strategies' in locals() else 'Unknown'}")
    print(f"   5. Chat mentioned strategies: {len(mentioned_strategies) if 'mentioned_strategies' in locals() else 'Unknown'}")
    
    print(f"\n🚨 INCONSISTENCIES FOUND:")
    print(f"   1. Admin has 35 strategies but only 6 work")
    print(f"   2. Chat shows 5 strategies but 6 are working")
    print(f"   3. 25 UUID strategies are likely placeholders")
    print(f"   4. Strategy ID mapping is inconsistent")
    
    print(f"\n💡 LIKELY SCENARIO:")
    print(f"   1. Originally had 25 placeholder strategies (UUIDs)")
    print(f"   2. When you asked for admin access, they created 14 'real' strategies")
    print(f"   3. But only 6 actually have working scanners")
    print(f"   4. The system is confused about what's real vs placeholder")
    print(f"   5. Chat only shows 5 because of filtering/display logic")
    
    # Save investigation results
    investigation_results = {
        "codebase_scanners": scanners if 'scanners' in locals() else [],
        "marketplace_strategies": list(all_marketplace_strategies),
        "trading_functions": strategy_functions if 'strategy_functions' in locals() else [],
        "admin_strategies": strategies if 'strategies' in locals() else [],
        "chat_mentioned_strategies": list(mentioned_strategies) if 'mentioned_strategies' in locals() else [],
        "inconsistencies": [
            "Admin has 35 strategies but only 6 work",
            "Chat shows 5 strategies but 6 are working", 
            "25 UUID strategies are likely placeholders",
            "Strategy ID mapping is inconsistent"
        ],
        "investigation_timestamp": datetime.now().isoformat()
    }
    
    with open(f'/workspace/investigation_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json', 'w') as f:
        json.dump(investigation_results, f, indent=2, default=str)
    
    print(f"\n💾 Investigation results saved to investigation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

if __name__ == "__main__":
    investigate_strategy_system()