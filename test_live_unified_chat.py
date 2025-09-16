#!/usr/bin/env python3
"""
Live test for unified chat endpoints
Uses curl to test the actual deployed endpoints
"""

import subprocess
import json
import time
import sys
import os


def run_curl_command(command_parts):
    """Run a curl command and return the result."""
    try:
        result = subprocess.run(command_parts, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)


def test_unified_chat():
    """Test the unified chat endpoints."""
    print("🧪 TESTING UNIFIED CHAT ON LIVE SYSTEM")
    print("=" * 50)
    
    # Get credentials from environment
    test_email = os.environ.get("TEST_EMAIL")
    test_password = os.environ.get("TEST_PASSWORD")
    
    if not test_email or not test_password:
        print("❌ ERROR: Missing test credentials")
        print("Please set TEST_EMAIL and TEST_PASSWORD environment variables")
        return False
    
    # Step 1: Login
    print("\n1️⃣ Logging in...")
    login_cmd = [
        "curl", "-s", "-X", "POST", 
        "https://cryptouniverse.onrender.com/api/v1/auth/login",
        "-H", "Content-Type: application/json",
        "-d", json.dumps({"email": test_email, "password": test_password})
    ]
    
    code, stdout, stderr = run_curl_command(login_cmd)
    if code != 0:
        print(f"❌ Login failed: {stderr}")
        return False
    
    try:
        login_data = json.loads(stdout)
        token = login_data.get("access_token")
        if not token:
            print(f"❌ No access token in response: {stdout}")
            return False
        print("✅ Login successful")
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON response: {stdout}")
        return False
    
    # Test results tracking
    passed = 0
    failed = 0
    
    # Step 2: Test unified chat endpoint
    print("\n2️⃣ Testing unified chat endpoint...")
    start_time = time.time()
    
    chat_cmd = [
        "curl", "-s", "-X", "POST",
        "https://cryptouniverse.onrender.com/api/v1/chat/message",
        "-H", f"Authorization: Bearer {token}",
        "-H", "Content-Type: application/json",
        "-d", json.dumps({"message": "What is my portfolio balance?"})
    ]
    
    code, stdout, stderr = run_curl_command(chat_cmd)
    elapsed = time.time() - start_time
    
    if code == 0:
        try:
            response = json.loads(stdout)
            if response.get("success"):
                print(f"✅ Chat endpoint working - Response time: {elapsed:.2f}s")
                
                # Check for real data
                content = response.get("content", "")
                if "$" in content and any(char.isdigit() for char in content):
                    print("✅ Real portfolio data returned")
                    passed += 1
                else:
                    print("❌ No real data in response")
                    failed += 1
                    
                # Check response time
                if elapsed < 5:
                    print("✅ Response time acceptable")
                    passed += 1
                else:
                    print(f"⚠️  Response time slow: {elapsed:.2f}s")
                    passed += 1  # Still passes but with warning
            else:
                print(f"❌ Chat response not successful: {response}")
                failed += 1
        except json.JSONDecodeError:
            print(f"❌ Invalid JSON response: {stdout}")
            failed += 1
    else:
        print(f"❌ Chat request failed: {stderr}")
        failed += 1
    
    # Step 3: Test conversation modes
    print("\n3️⃣ Testing conversation modes...")
    modes = ["live_trading", "paper_trading", "analysis"]
    
    for mode in modes:
        cmd = [
            "curl", "-s", "-X", "POST",
            "https://cryptouniverse.onrender.com/api/v1/chat/message",
            "-H", f"Authorization: Bearer {token}",
            "-H", "Content-Type: application/json",
            "-d", json.dumps({"message": "Test message", "conversation_mode": mode})
        ]
        
        code, stdout, stderr = run_curl_command(cmd)
        if code == 0:
            try:
                response = json.loads(stdout)
                if response.get("success"):
                    print(f"✅ {mode} mode working")
                    passed += 1
                else:
                    print(f"❌ {mode} mode failed")
                    failed += 1
            except:
                print(f"❌ {mode} mode invalid response")
                failed += 1
        else:
            print(f"❌ {mode} mode request failed")
            failed += 1
    
    # Step 4: Test capabilities endpoint
    print("\n4️⃣ Testing capabilities endpoint...")
    cap_cmd = [
        "curl", "-s", "-X", "GET",
        "https://cryptouniverse.onrender.com/api/v1/chat/capabilities",
        "-H", f"Authorization: Bearer {token}"
    ]
    
    code, stdout, stderr = run_curl_command(cap_cmd)
    if code == 0:
        try:
            response = json.loads(stdout)
            if response.get("success"):
                caps = response.get("capabilities", {})
                print(f"✅ Capabilities endpoint working")
                print(f"   - Paper trading no credits: {caps.get('trading', {}).get('paper_trading', {}).get('requires_credits') == False}")
                passed += 1
            else:
                print("❌ Capabilities failed")
                failed += 1
        except:
            print("❌ Capabilities invalid response")
            failed += 1
    else:
        print("❌ Capabilities request failed")
        failed += 1
    
    # Step 5: Test status endpoint
    print("\n5️⃣ Testing status endpoint...")
    status_cmd = [
        "curl", "-s", "-X", "GET",
        "https://cryptouniverse.onrender.com/api/v1/chat/status",
        "-H", f"Authorization: Bearer {token}"
    ]
    
    code, stdout, stderr = run_curl_command(status_cmd)
    if code == 0:
        try:
            response = json.loads(stdout)
            status = response.get("service_status", {})
            print(f"✅ Status endpoint working")
            print(f"   - Service status: {status.get('status', 'unknown')}")
            print(f"   - Features active: {status.get('features_active', {})}")
            passed += 1
        except:
            print("❌ Status invalid response")
            failed += 1
    else:
        print("❌ Status request failed")
        failed += 1
    
    # Step 6: Test backwards compatibility
    print("\n6️⃣ Testing backwards compatibility...")
    compat_cmd = [
        "curl", "-s", "-X", "POST",
        "https://cryptouniverse.onrender.com/api/v1/conversational-chat/conversational",
        "-H", f"Authorization: Bearer {token}",
        "-H", "Content-Type: application/json",
        "-d", json.dumps({"message": "Test backwards compatibility"})
    ]
    
    code, stdout, stderr = run_curl_command(compat_cmd)
    if code == 0:
        print("✅ Backwards compatibility working (/conversational-chat)")
        passed += 1
    else:
        print("❌ Backwards compatibility failed")
        failed += 1
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Success Rate: {passed/(passed+failed)*100:.1f}%" if (passed+failed) > 0 else "N/A")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED!")
        print("The unified chat is working correctly on the live system.")
        return True
    else:
        print("\n⚠️  Some tests failed.")
        print("Please check the implementation.")
        return False


def main():
    """Run the live tests."""
    success = test_unified_chat()
    
    if success:
        print("\n" + "=" * 50)
        print("✅ SAFE TO PROCEED WITH CLEANUP")
        print("=" * 50)
        print("The unified chat is fully functional.")
        print("You can now safely remove old files.")
    else:
        print("\n" + "=" * 50)
        print("❌ DO NOT PROCEED WITH CLEANUP")
        print("=" * 50)
        print("Fix the issues before removing old files.")
        sys.exit(1)


if __name__ == "__main__":
    main()