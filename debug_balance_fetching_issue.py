#!/usr/bin/env python3
"""
Debug Balance Fetching Issue
Focus: Why are individual balances showing as 0 when total portfolio value is correct?
"""

import asyncio
import httpx
import json
from datetime import datetime

# Configuration
BASE_URL = "https://cryptouniverse.onrender.com"
LOGIN_DATA = {
    "email": "admin@cryptouniverse.com",
    "password": "AdminPass123!"
}

class BalanceFetchingDebugger:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=120.0)
        self.token = None
        
    async def authenticate(self):
        """Authenticate and get token"""
        print("🔐 Authenticating...")
        response = await self.client.post(f"{BASE_URL}/api/v1/auth/login", json=LOGIN_DATA)
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.client.headers.update({"Authorization": f"Bearer {self.token}"})
            print("✅ Authentication successful")
            return True
        else:
            print(f"❌ Authentication failed: {response.status_code}")
            return False
    
    async def debug_raw_portfolio_structure(self):
        """Debug the raw portfolio API response structure"""
        print("\n" + "="*80)
        print("🔍 DEBUGGING RAW PORTFOLIO STRUCTURE")
        print("="*80)
        
        try:
            portfolio_response = await self.client.get(f"{BASE_URL}/api/v1/trading/portfolio")
            if portfolio_response.status_code == 200:
                portfolio_data = portfolio_response.json()
                
                print(f"✅ Portfolio API Response Structure:")
                print(f"   Status Code: {portfolio_response.status_code}")
                print(f"   Response Keys: {list(portfolio_data.keys())}")
                
                # Check total value
                total_value = portfolio_data.get('total_value')
                print(f"   Total Value: {total_value} (type: {type(total_value)})")
                
                # Check positions structure
                positions = portfolio_data.get('positions', [])
                print(f"   Positions Count: {len(positions)}")
                print(f"   Positions Type: {type(positions)}")
                
                if positions:
                    print(f"\n   First 5 Position Details:")
                    for i, pos in enumerate(positions[:5]):
                        print(f"   Position {i+1}:")
                        print(f"     Keys: {list(pos.keys()) if isinstance(pos, dict) else 'Not a dict'}")
                        if isinstance(pos, dict):
                            symbol = pos.get('symbol', 'N/A')
                            amount = pos.get('amount', 'N/A')
                            value_usd = pos.get('value_usd', 'N/A')
                            print(f"     Symbol: {symbol}")
                            print(f"     Amount: {amount} (type: {type(amount)})")
                            print(f"     Value USD: {value_usd} (type: {type(value_usd)})")
                else:
                    print("   ❌ No positions found in response")
                
                # Check if there are other balance-related fields
                for key, value in portfolio_data.items():
                    if key not in ['total_value', 'positions']:
                        print(f"   Other field - {key}: {value} (type: {type(value)})")
                
                return portfolio_data
            else:
                print(f"❌ Portfolio API Failed: {portfolio_response.status_code}")
                print(f"   Response: {portfolio_response.text}")
                return None
        except Exception as e:
            print(f"❌ Portfolio API Error: {e}")
            return None
    
    async def debug_exchange_accounts(self):
        """Debug user's exchange accounts"""
        print("\n📊 DEBUGGING EXCHANGE ACCOUNTS")
        print("-" * 40)
        
        try:
            # Try to get exchange accounts
            exchanges_response = await self.client.get(f"{BASE_URL}/api/v1/exchanges/accounts")
            if exchanges_response.status_code == 200:
                exchanges_data = exchanges_response.json()
                print(f"✅ Exchange Accounts Retrieved")
                print(f"   Accounts Count: {len(exchanges_data)}")
                
                for i, account in enumerate(exchanges_data[:3]):  # Show first 3
                    print(f"   Account {i+1}:")
                    print(f"     Exchange: {account.get('exchange_name', 'N/A')}")
                    print(f"     Status: {account.get('status', 'N/A')}")
                    print(f"     ID: {account.get('id', 'N/A')}")
                
                return exchanges_data
            else:
                print(f"❌ Exchange Accounts API Failed: {exchanges_response.status_code}")
                print(f"   Response: {exchanges_response.text}")
                return None
        except Exception as e:
            print(f"❌ Exchange Accounts API Error: {e}")
            return None
    
    async def debug_exchange_balances(self):
        """Debug exchange balance fetching"""
        print("\n📊 DEBUGGING EXCHANGE BALANCES")
        print("-" * 40)
        
        try:
            # Try to get balances directly
            balances_response = await self.client.get(f"{BASE_URL}/api/v1/exchanges/balances")
            if balances_response.status_code == 200:
                balances_data = balances_response.json()
                print(f"✅ Exchange Balances Retrieved")
                print(f"   Response Keys: {list(balances_data.keys())}")
                
                # Check if there's a balances array
                if 'balances' in balances_data:
                    balances = balances_data['balances']
                    print(f"   Balances Count: {len(balances)}")
                    
                    # Show first few balances with details
                    for i, balance in enumerate(balances[:5]):
                        print(f"   Balance {i+1}:")
                        if isinstance(balance, dict):
                            asset = balance.get('asset', 'N/A')
                            total = balance.get('total', 'N/A')
                            value_usd = balance.get('value_usd', 'N/A')
                            exchange = balance.get('exchange', 'N/A')
                            print(f"     Asset: {asset}")
                            print(f"     Total: {total} (type: {type(total)})")
                            print(f"     Value USD: {value_usd} (type: {type(value_usd)})")
                            print(f"     Exchange: {exchange}")
                        else:
                            print(f"     Raw: {balance}")
                
                # Check total value
                if 'total_value_usd' in balances_data:
                    total_value = balances_data['total_value_usd']
                    print(f"   Total Value USD: {total_value} (type: {type(total_value)})")
                
                return balances_data
            else:
                print(f"❌ Exchange Balances API Failed: {balances_response.status_code}")
                print(f"   Response: {balances_response.text}")
                return None
        except Exception as e:
            print(f"❌ Exchange Balances API Error: {e}")
            return None
    
    async def run_complete_debug(self):
        """Run complete debugging sequence"""
        print("🔍 Starting Balance Fetching Debug")
        print(f"🌐 Target: {BASE_URL}")
        print(f"⏰ Started: {datetime.now()}")
        
        if not await self.authenticate():
            return
        
        # Debug sequence
        portfolio_data = await self.debug_raw_portfolio_structure()
        exchange_accounts = await self.debug_exchange_accounts()
        exchange_balances = await self.debug_exchange_balances()
        
        # Analysis
        print("\n" + "="*80)
        print("🎯 BALANCE FETCHING ANALYSIS")
        print("="*80)
        
        if portfolio_data:
            total_value = portfolio_data.get('total_value', 0)
            positions = portfolio_data.get('positions', [])
            
            print(f"📊 Portfolio Analysis:")
            print(f"   Total Value: ${total_value}")
            print(f"   Positions Count: {len(positions)}")
            
            # Check if positions have actual values
            positions_with_value = [p for p in positions if isinstance(p, dict) and p.get('value_usd', 0) > 0]
            positions_with_amount = [p for p in positions if isinstance(p, dict) and p.get('amount', 0) > 0]
            
            print(f"   Positions with Value > 0: {len(positions_with_value)}")
            print(f"   Positions with Amount > 0: {len(positions_with_amount)}")
            
            if len(positions_with_value) == 0 and total_value > 0:
                print(f"🎯 ISSUE IDENTIFIED:")
                print(f"   ❌ Portfolio has total value (${total_value})")
                print(f"   ❌ But no positions have individual values")
                print(f"   📍 LIKELY CAUSE: Balance aggregation or filtering issue")
        
        if exchange_balances:
            balances = exchange_balances.get('balances', [])
            total_exchange_value = exchange_balances.get('total_value_usd', 0)
            
            print(f"\n📊 Exchange Balance Analysis:")
            print(f"   Exchange Total Value: ${total_exchange_value}")
            print(f"   Exchange Balances Count: {len(balances)}")
            
            # Check if exchange balances have values
            balances_with_value = [b for b in balances if isinstance(b, dict) and b.get('value_usd', 0) > 0]
            balances_with_total = [b for b in balances if isinstance(b, dict) and b.get('total', 0) > 0]
            
            print(f"   Balances with Value > 0: {len(balances_with_value)}")
            print(f"   Balances with Total > 0: {len(balances_with_total)}")
            
            if len(balances_with_total) > 0:
                print(f"✅ Exchange balances have proper totals")
                print(f"   Sample balance with total:")
                for balance in balances_with_total[:1]:
                    print(f"     {balance.get('asset')}: {balance.get('total')} = ${balance.get('value_usd')}")
            else:
                print(f"❌ No exchange balances have totals > 0")
        
        await self.client.aclose()
        print(f"\n⏰ Debug completed: {datetime.now()}")

async def main():
    debugger = BalanceFetchingDebugger()
    await debugger.run_complete_debug()

if __name__ == "__main__":
    asyncio.run(main())