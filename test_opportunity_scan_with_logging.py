#!/usr/bin/env python3
"""
Test opportunity scan and monitor logs in real-time.
This script initiates a scan and monitors the status/results endpoints to identify issues.
"""

import os
import sys
import asyncio
import json
import time
import requests
from datetime import datetime
from typing import Dict, Optional

# Configuration
BASE_URL = os.environ.get("BASE_URL", "https://cryptouniverse.onrender.com")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@cryptouniverse.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "AdminPass123!")

class OpportunityScanTester:
    def __init__(self, base_url: str, email: str, password: str):
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.password = password
        self.session = requests.Session()
        self.token: Optional[str] = None
        self.user_id: Optional[str] = None
        
    def login(self) -> bool:
        """Login and get auth token."""
        print(f"\n🔐 Logging in as {self.email}...")
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/auth/login",
                json={"email": self.email, "password": self.password},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.user_id = data.get("user", {}).get("id")
                if self.token:
                    self.session.headers.update({
                        "Authorization": f"Bearer {self.token}"
                    })
                    print(f"✅ Login successful. User ID: {self.user_id}")
                    return True
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            return False
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
    
    def initiate_scan(self) -> Optional[Dict]:
        """Initiate an opportunity scan."""
        print("\n🚀 Initiating opportunity scan...")
        try:
            response = self.session.post(
                f"{self.base_url}/api/v1/opportunities/discover",
                json={},
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                scan_id = data.get("scan_id")
                print(f"✅ Scan initiated. Scan ID: {scan_id}")
                return data
            else:
                print(f"❌ Scan initiation failed: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"❌ Scan initiation error: {e}")
            return None
    
    def get_scan_status(self, scan_id: str) -> Optional[Dict]:
        """Get scan status."""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/opportunities/status/{scan_id}",
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return {"status": "not_found", "error": response.text}
            else:
                return {"status": "error", "error": f"{response.status_code}: {response.text}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def get_scan_results(self, scan_id: str) -> Optional[Dict]:
        """Get scan results."""
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/opportunities/results/{scan_id}",
                timeout=10
            )
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return {"status": "not_found", "error": response.text}
            else:
                return {"status": "error", "error": f"{response.status_code}: {response.text}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def monitor_scan(self, scan_id: str, max_polls: int = 60, poll_interval: int = 3):
        """Monitor scan progress."""
        print(f"\n📊 Monitoring scan {scan_id}...")
        print(f"   Polling every {poll_interval}s for up to {max_polls} polls ({max_polls * poll_interval}s total)")
        
        status_history = []
        results_attempts = []
        
        for poll_num in range(1, max_polls + 1):
            status = self.get_scan_status(scan_id)
            timestamp = datetime.now().isoformat()
            
            if status:
                status_value = status.get("status", "unknown")
                progress = status.get("progress", {})
                strategies_completed = progress.get("strategies_completed", 0)
                total_strategies = progress.get("total_strategies", 0)
                
                status_history.append({
                    "poll": poll_num,
                    "timestamp": timestamp,
                    "status": status_value,
                    "strategies_completed": strategies_completed,
                    "total_strategies": total_strategies,
                    "full_response": status
                })
                
                # Print status
                if poll_num == 1 or poll_num % 10 == 0 or status_value in ["complete", "failed"]:
                    print(f"  Poll {poll_num:3d}: status={status_value:12s} "
                          f"progress={strategies_completed}/{total_strategies} strategies")
                
                # Check if complete
                if status_value == "complete":
                    print(f"\n✅ Scan completed at poll {poll_num}")
                    
                    # Try to get results
                    print("\n📥 Fetching scan results...")
                    for attempt in range(1, 6):
                        results = self.get_scan_results(scan_id)
                        results_attempts.append({
                            "attempt": attempt,
                            "timestamp": datetime.now().isoformat(),
                            "results": results
                        })
                        
                        if results and results.get("status") != "not_found":
                            print(f"✅ Results fetched successfully on attempt {attempt}")
                            return {
                                "status_history": status_history,
                                "results_attempts": results_attempts,
                                "final_status": status,
                                "final_results": results
                            }
                        else:
                            print(f"  Attempt {attempt}: Results not available (status: {results.get('status') if results else 'None'})")
                            time.sleep(2)
                    
                    return {
                        "status_history": status_history,
                        "results_attempts": results_attempts,
                        "final_status": status,
                        "final_results": None
                    }
                
                elif status_value == "failed":
                    print(f"\n❌ Scan failed at poll {poll_num}")
                    return {
                        "status_history": status_history,
                        "results_attempts": results_attempts,
                        "final_status": status,
                        "final_results": None
                    }
            
            time.sleep(poll_interval)
        
        print(f"\n⏱️  Monitoring timeout after {max_polls} polls")
        return {
            "status_history": status_history,
            "results_attempts": results_attempts,
            "final_status": None,
            "final_results": None
        }
    
    def analyze_results(self, monitoring_results: Dict):
        """Analyze monitoring results."""
        print("\n" + "="*80)
        print("ANALYSIS")
        print("="*80)
        
        status_history = monitoring_results.get("status_history", [])
        results_attempts = monitoring_results.get("results_attempts", [])
        
        if not status_history:
            print("❌ No status history collected")
            return
        
        # Analyze status patterns
        status_counts = {}
        not_found_count = 0
        scanning_count = 0
        complete_count = 0
        
        for entry in status_history:
            status = entry.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
            
            if status == "not_found":
                not_found_count += 1
            elif status == "scanning":
                scanning_count += 1
            elif status == "complete":
                complete_count += 1
        
        print(f"\n📊 Status Distribution:")
        for status, count in sorted(status_counts.items(), key=lambda x: -x[1]):
            percentage = (count / len(status_history)) * 100
            print(f"  {status:15s}: {count:3d} ({percentage:5.1f}%)")
        
        # Check for intermittent not_found
        if not_found_count > 0:
            print(f"\n⚠️  Intermittent 'not_found' detected: {not_found_count}/{len(status_history)} polls")
            print("   This indicates lookup key issues.")
            
            # Find patterns
            not_found_polls = [e["poll"] for e in status_history if e.get("status") == "not_found"]
            scanning_polls = [e["poll"] for e in status_history if e.get("status") == "scanning"]
            complete_polls = [e["poll"] for e in status_history if e.get("status") == "complete"]
            
            if not_found_polls:
                print(f"   'not_found' occurred at polls: {not_found_polls[:10]}...")
            if scanning_polls:
                print(f"   'scanning' occurred at polls: {scanning_polls[:10]}...")
            if complete_polls:
                print(f"   'complete' occurred at polls: {complete_polls}")
        
        # Analyze results endpoint
        if results_attempts:
            print(f"\n📥 Results Endpoint Attempts: {len(results_attempts)}")
            successful = [r for r in results_attempts if r.get("results", {}).get("status") != "not_found"]
            failed = [r for r in results_attempts if r.get("results", {}).get("status") == "not_found"]
            
            print(f"   Successful: {len(successful)}")
            print(f"   Failed (not_found): {len(failed)}")
            
            if failed:
                print(f"\n❌ Results endpoint returned 'not_found' {len(failed)} times")
                print("   This indicates cache key resolution is failing.")
        
        # Save detailed results
        output_file = f"opportunity_scan_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(monitoring_results, f, indent=2, default=str)
        print(f"\n💾 Detailed results saved to: {output_file}")

def main():
    """Main function."""
    print("="*80)
    print("OPPORTUNITY SCAN TEST WITH LOGGING")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"Email: {ADMIN_EMAIL}")
    
    tester = OpportunityScanTester(BASE_URL, ADMIN_EMAIL, ADMIN_PASSWORD)
    
    # Login
    if not tester.login():
        print("\n❌ Cannot proceed without authentication")
        return 1
    
    # Initiate scan
    scan_data = tester.initiate_scan()
    if not scan_data:
        print("\n❌ Cannot proceed without scan ID")
        return 1
    
    scan_id = scan_data.get("scan_id")
    if not scan_id:
        print("\n❌ No scan_id in response")
        return 1
    
    # Monitor scan
    monitoring_results = tester.monitor_scan(scan_id, max_polls=60, poll_interval=3)
    
    # Analyze results
    tester.analyze_results(monitoring_results)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
