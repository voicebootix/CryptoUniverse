"""
Comprehensive Opportunity Scan Test
Tests the opportunity discovery endpoint and monitors logs in parallel.
"""
import asyncio
import httpx
import json
import sys
from datetime import datetime
from typing import Optional, Dict, Any

BASE_URL = "https://cryptouniverse.onrender.com"
EMAIL = "admin@cryptouniverse.com"
PASSWORD = "AdminPass123!"

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


async def login(client: httpx.AsyncClient) -> Optional[str]:
    """Login and get access token."""
    print(f"\n[LOGIN] Logging in as {EMAIL}...")
    try:
        response = await client.post(
            f"{BASE_URL}/api/v1/auth/login",
            json={"email": EMAIL, "password": PASSWORD}
        )
        response.raise_for_status()
        data = response.json()
        token = data.get("access_token")
        if token:
            print(f"[OK] Login successful! Token: {token[:50]}...")
            return token
        else:
            print(f"[ERROR] No token in response: {data}")
            return None
    except Exception as e:
        print(f"[ERROR] Login failed: {e}")
        return None


async def initiate_scan(client: httpx.AsyncClient, token: str) -> Optional[Dict[str, Any]]:
    """Initiate opportunity scan."""
    print(f"\n[SCAN] Initiating opportunity scan...")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.post(
            f"{BASE_URL}/api/v1/opportunities/discover",
            json={
                "force_refresh": True,
                "include_strategy_recommendations": True
            },
            headers=headers,
            timeout=30.0
        )
        response.raise_for_status()
        data = response.json()
        
        print(f"[RESPONSE] Status: {response.status_code}")
        print(f"[RESPONSE] Data: {json.dumps(data, indent=2)}")
        
        scan_id = data.get("scan_id")
        if scan_id:
            print(f"[OK] Scan initiated successfully! Scan ID: {scan_id}")
            return data
        else:
            print(f"[ERROR] No scan_id in response")
            return None
    except httpx.TimeoutException:
        print(f"[ERROR] Request timed out!")
        return None
    except Exception as e:
        print(f"[ERROR] Scan initiation failed: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"[ERROR] Response: {e.response.text}")
        return None


async def check_status(client: httpx.AsyncClient, token: str, scan_id: str) -> Optional[Dict[str, Any]]:
    """Check scan status."""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get(
            f"{BASE_URL}/api/v1/opportunities/status/{scan_id}",
            headers=headers,
            timeout=10.0
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[WARN] Status check failed: {e}")
        return None


async def get_results(client: httpx.AsyncClient, token: str, scan_id: str) -> Optional[Dict[str, Any]]:
    """Get scan results."""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get(
            f"{BASE_URL}/api/v1/opportunities/results/{scan_id}",
            headers=headers,
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[WARN] Results fetch failed: {e}")
        return None


async def poll_scan_status(client: httpx.AsyncClient, token: str, scan_id: str, max_polls: int = 60) -> Dict[str, Any]:
    """Poll scan status until completion."""
    print(f"\n[STATUS] Polling scan status (scan_id: {scan_id})...")
    
    for poll_num in range(1, max_polls + 1):
        status_data = await check_status(client, token, scan_id)
        
        if not status_data:
            print(f"[POLL {poll_num}] Status check failed")
            await asyncio.sleep(3)
            continue
        
        status = status_data.get("status", "unknown")
        progress = status_data.get("progress", {})
        strategies_completed = progress.get("strategies_completed", 0)
        total_strategies = progress.get("total_strategies", 0)
        opportunities_found = progress.get("opportunities_found_so_far", 0)
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[POLL {poll_num}] [{timestamp}] Status: {status} | "
              f"Strategies: {strategies_completed}/{total_strategies} | "
              f"Opportunities: {opportunities_found}")
        
        if status in ["completed", "finished"]:
            print(f"[OK] Scan completed!")
            return status_data
        elif status == "failed":
            print(f"[ERROR] Scan failed!")
            return status_data
        
        await asyncio.sleep(3)
    
    print(f"[WARN] Max polls reached, checking final status...")
    return await check_status(client, token, scan_id) or {}


async def analyze_results(results: Dict[str, Any]) -> None:
    """Analyze and validate scan results."""
    print("\n" + "=" * 80)
    print("RESULTS ANALYSIS")
    print("=" * 80)
    
    if not results:
        print("[ERROR] No results to analyze")
        return
    
    success = results.get("success", False)
    status = results.get("status", "unknown")
    opportunities = results.get("opportunities", [])
    metadata = results.get("metadata", {})
    
    print(f"\n[SUMMARY]")
    print(f"  Success: {success}")
    print(f"  Status: {status}")
    print(f"  Total Opportunities: {len(opportunities)}")
    print(f"  Strategies Completed: {metadata.get('strategies_completed', 0)}")
    print(f"  Total Strategies: {metadata.get('total_strategies', 0)}")
    print(f"  Scan Duration: {metadata.get('scan_duration_seconds', 0):.2f}s")
    
    if opportunities:
        print(f"\n[OPPORTUNITIES]")
        for i, opp in enumerate(opportunities[:10], 1):  # Show first 10
            strategy_name = opp.get("strategy_name", "Unknown")
            symbol = opp.get("symbol", "Unknown")
            opportunity_type = opp.get("opportunity_type", "Unknown")
            profit_potential = opp.get("profit_potential_usd", 0)
            confidence = opp.get("confidence_score", 0)
            
            print(f"  {i}. {strategy_name} | {symbol} | {opportunity_type}")
            print(f"     Profit: ${profit_potential:.2f} | Confidence: {confidence:.2f}")
        
        if len(opportunities) > 10:
            print(f"  ... and {len(opportunities) - 10} more opportunities")
        
        # Validate opportunity structure
        print(f"\n[VALIDATION]")
        required_fields = ["strategy_id", "strategy_name", "symbol", "opportunity_type"]
        valid_count = 0
        invalid_count = 0
        
        for opp in opportunities:
            has_all_fields = all(field in opp for field in required_fields)
            if has_all_fields:
                valid_count += 1
            else:
                invalid_count += 1
                missing = [f for f in required_fields if f not in opp]
                print(f"  [INVALID] Missing fields: {missing}")
        
        print(f"  Valid opportunities: {valid_count}/{len(opportunities)}")
        if invalid_count > 0:
            print(f"  Invalid opportunities: {invalid_count}")
    else:
        print(f"\n[WARNING] No opportunities found")
    
    print("\n" + "=" * 80)


async def main():
    print("=" * 80)
    print("OPPORTUNITY SCAN COMPREHENSIVE TEST")
    print("=" * 80)
    
    async with httpx.AsyncClient() as client:
        # Step 1: Login
        token = await login(client)
        if not token:
            print("\n[ERROR] Cannot proceed without authentication token")
            return
        
        # Step 2: Initiate scan
        scan_response = await initiate_scan(client, token)
        if not scan_response:
            print("\n[ERROR] Scan initiation failed")
            return
        
        scan_id = scan_response.get("scan_id")
        if not scan_id:
            print("\n[ERROR] No scan_id returned")
            return
        
        # Step 3: Poll status
        final_status = await poll_scan_status(client, token, scan_id)
        
        # Step 4: Get results
        print(f"\n[RESULTS] Fetching final results...")
        results = await get_results(client, token, scan_id)
        
        # Step 5: Analyze results
        if results:
            await analyze_results(results)
            
            # Save results to file
            output_file = f"opportunity_scan_results_{scan_id}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"\n[SAVED] Results saved to {output_file}")
        else:
            print(f"\n[ERROR] Could not fetch results")
        
        print("\n" + "=" * 80)
        print("[OK] Test completed! Check server logs for details.")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

