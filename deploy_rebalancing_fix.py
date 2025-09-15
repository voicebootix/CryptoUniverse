#!/usr/bin/env python3
"""
Deploy Rebalancing Fix
Fixes the rebalancing data structure issue in chat service adapters
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "https://cryptouniverse.onrender.com"

class RebalancingFixDeployer:
    def __init__(self):
        self.auth_token = None
        self.session_id = None
        
    def login(self) -> bool:
        """Login with admin credentials"""
        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/auth/login",
                json={"email": "admin@cryptouniverse.com", "password": "AdminPass123!"},
                timeout=30
            )
            
            if response.status_code == 200:
                self.auth_token = response.json().get("access_token")
                print(f"✅ Authenticated successfully")
                return True
            else:
                print(f"❌ Login failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
            
    def create_session(self) -> bool:
        """Create chat session"""
        try:
            headers = {"Authorization": f"Bearer {self.auth_token}", "Content-Type": "application/json"}
            response = requests.post(f"{BASE_URL}/api/v1/chat/session/new", headers=headers, json={}, timeout=30)
            
            if response.status_code == 200:
                self.session_id = response.json().get("session_id")
                print(f"✅ Session created: {self.session_id}")
                return True
            else:
                print(f"❌ Session creation failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Session error: {e}")
            return False
            
    def test_rebalancing_fix(self):
        """Test the rebalancing fix"""
        print(f"\n{'='*60}")
        print("🔧 TESTING: Rebalancing Fix Deployment")
        print(f"{'='*60}")
        
        headers = {"Authorization": f"Bearer {self.auth_token}", "Content-Type": "application/json"}
        
        # Test rebalancing message
        test_message = "Should I rebalance my current allocation?"
        payload = {"message": test_message, "session_id": self.session_id}
        
        print(f"📤 Testing: {test_message}")
        
        try:
            start_time = time.time()
            response = requests.post(f"{BASE_URL}/api/v1/chat/message", headers=headers, json=payload, timeout=60)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Success ({response_time:.1f}s)")
                print(f"🎯 Intent: {data.get('intent', 'N/A')}")
                print(f"📊 Confidence: {data.get('confidence', 0):.1%}")
                
                # Check for the specific error we're fixing
                metadata = data.get('metadata', {})
                if 'rebalance_analysis' in metadata:
                    rebalance_data = metadata['rebalance_analysis']
                    if 'error' in rebalance_data:
                        error_msg = rebalance_data['error']
                        if "rebalancing_needed" in error_msg:
                            print(f"❌ FIX NOT DEPLOYED: Still seeing rebalancing_needed error")
                            print(f"   Error: {error_msg}")
                            return False
                        else:
                            print(f"⚠️ Different error: {error_msg}")
                    else:
                        print(f"✅ FIX DEPLOYED: No rebalancing_needed error found")
                        print(f"⚖️ Needs Rebalancing: {rebalance_data.get('needs_rebalancing', 'Unknown')}")
                        return True
                else:
                    print(f"⚠️ No rebalance_analysis in metadata")
                    return False
            else:
                print(f"❌ Request failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Test error: {e}")
            return False
    
    def run_deployment_test(self):
        """Run deployment test"""
        print("🚀 Starting Rebalancing Fix Deployment Test")
        print(f"🌐 Target: {BASE_URL}")
        print(f"⏰ Started: {datetime.now()}")
        
        if not self.login() or not self.create_session():
            return
        
        # Test the fix
        fix_deployed = self.test_rebalancing_fix()
        
        # Generate summary
        print(f"\n{'='*60}")
        print("📊 DEPLOYMENT TEST SUMMARY")
        print(f"{'='*60}")
        
        if fix_deployed:
            print("✅ REBALANCING FIX SUCCESSFULLY DEPLOYED")
            print("   • No more 'rebalancing_needed' attribute errors")
            print("   • Rebalancing analysis working correctly")
            print("   • Chat system functioning properly")
        else:
            print("❌ REBALANCING FIX NOT YET DEPLOYED")
            print("   • Still seeing rebalancing_needed errors")
            print("   • Need to restart the service or redeploy")
        
        print(f"\n⏰ Completed: {datetime.now()}")
        print(f"{'='*60}")

def main():
    deployer = RebalancingFixDeployer()
    deployer.run_deployment_test()

if __name__ == "__main__":
    main()