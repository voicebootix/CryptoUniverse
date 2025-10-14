#!/usr/bin/env python3
"""
Comprehensive Chat Endpoint Testing Suite
Tests the deployed cryptouniverse.onrender.com server to verify fixes
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
from typing import Dict, Any, List


class ChatEndpointTester:
    """Comprehensive chat endpoint testing with detailed reporting."""
    
    def __init__(self):
        self.base_url = "https://cryptouniverse.onrender.com"
        self.session = None
        self.test_results = []
        self.admin_credentials = {
            "email": "admin@cryptouniverse.com",
            "password": "AdminPass123!"
        }
        self.auth_token = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=60),
            headers={"Content-Type": "application/json"}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def authenticate(self) -> bool:
        """Authenticate and get access token."""
        print("🔐 Authenticating with admin credentials...")
        
        try:
            async with self.session.post(
                f"{self.base_url}/api/v1/auth/login",
                json=self.admin_credentials
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.auth_token = data.get("access_token")
                    print(f"✅ Authentication successful")
                    return True
                else:
                    print(f"❌ Authentication failed: {response.status}")
                    print(f"Response: {await response.text()}")
                    return False
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False
    
    async def test_health_endpoint(self) -> Dict[str, Any]:
        """Test the health endpoint."""
        print("\n🏥 Testing health endpoint...")
        
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                status = response.status
                data = await response.json() if response.content_type == 'application/json' else await response.text()
                
                result = {
                    "endpoint": "/health",
                    "status_code": status,
                    "response": data,
                    "success": status == 200,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                if status == 200:
                    print(f"✅ Health check passed: {status}")
                else:
                    print(f"❌ Health check failed: {status}")
                
                return result
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return {
                "endpoint": "/health",
                "status_code": 0,
                "error": str(e),
                "success": False,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def test_chat_message_endpoint(self, message: str) -> Dict[str, Any]:
        """Test the chat message endpoint with a specific message."""
        print(f"\n💬 Testing chat endpoint with message: '{message}'")
        
        if not self.auth_token:
            return {
                "endpoint": "/api/v1/chat/message",
                "status_code": 0,
                "error": "No auth token",
                "success": False,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "message": message,
            "session_id": f"test_session_{int(time.time())}"
        }
        
        try:
            start_time = time.time()
            async with self.session.post(
                f"{self.base_url}/api/v1/chat/message",
                json=payload,
                headers=headers
            ) as response:
                end_time = time.time()
                response_time = end_time - start_time
                
                status = response.status
                content_type = response.headers.get('content-type', '')
                
                if 'application/json' in content_type:
                    data = await response.json()
                else:
                    data = await response.text()
                
                result = {
                    "endpoint": "/api/v1/chat/message",
                    "message": message,
                    "status_code": status,
                    "response_time_seconds": round(response_time, 2),
                    "response": data,
                    "success": status == 200,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                if status == 200:
                    print(f"✅ Chat message successful: {status} ({response_time:.2f}s)")
                    if isinstance(data, dict) and 'response' in data:
                        print(f"   Response preview: {str(data['response'])[:200]}...")
                else:
                    print(f"❌ Chat message failed: {status} ({response_time:.2f}s)")
                    print(f"   Error: {str(data)[:200]}...")
                
                return result
        except asyncio.TimeoutError:
            print(f"⏰ Chat message timeout after 60s")
            return {
                "endpoint": "/api/v1/chat/message",
                "message": message,
                "status_code": 0,
                "error": "Timeout after 60s",
                "success": False,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            print(f"❌ Chat message error: {e}")
            return {
                "endpoint": "/api/v1/chat/message",
                "message": message,
                "status_code": 0,
                "error": str(e),
                "success": False,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def test_portfolio_endpoint(self) -> Dict[str, Any]:
        """Test the portfolio endpoint."""
        print(f"\n📊 Testing portfolio endpoint...")
        
        if not self.auth_token:
            return {
                "endpoint": "/api/v1/unified-strategies/portfolio",
                "status_code": 0,
                "error": "No auth token",
                "success": False,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }
        
        try:
            start_time = time.time()
            async with self.session.get(
                f"{self.base_url}/api/v1/unified-strategies/portfolio",
                headers=headers
            ) as response:
                end_time = time.time()
                response_time = end_time - start_time
                
                status = response.status
                content_type = response.headers.get('content-type', '')
                
                if 'application/json' in content_type:
                    data = await response.json()
                else:
                    data = await response.text()
                
                result = {
                    "endpoint": "/api/v1/unified-strategies/portfolio",
                    "status_code": status,
                    "response_time_seconds": round(response_time, 2),
                    "response": data,
                    "success": status == 200,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                if status == 200:
                    print(f"✅ Portfolio endpoint successful: {status} ({response_time:.2f}s)")
                    if isinstance(data, dict):
                        strategies_count = len(data.get('strategies', []))
                        print(f"   Strategies found: {strategies_count}")
                else:
                    print(f"❌ Portfolio endpoint failed: {status} ({response_time:.2f}s)")
                
                return result
        except asyncio.TimeoutError:
            print(f"⏰ Portfolio endpoint timeout after 60s")
            return {
                "endpoint": "/api/v1/unified-strategies/portfolio",
                "status_code": 0,
                "error": "Timeout after 60s",
                "success": False,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            print(f"❌ Portfolio endpoint error: {e}")
            return {
                "endpoint": "/api/v1/unified-strategies/portfolio",
                "status_code": 0,
                "error": str(e),
                "success": False,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def test_opportunity_discovery(self) -> Dict[str, Any]:
        """Test the opportunity discovery endpoint."""
        print(f"\n🔍 Testing opportunity discovery endpoint...")
        
        if not self.auth_token:
            return {
                "endpoint": "/api/v1/opportunities/discover",
                "status_code": 0,
                "error": "No auth token",
                "success": False,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "risk_tolerance": "moderate",
            "investment_objectives": ["growth", "balanced"],
            "time_horizon": "medium_term",
            "investment_amount": 5000,
            "constraints": ["no_leverage"]
        }
        
        try:
            start_time = time.time()
            async with self.session.post(
                f"{self.base_url}/api/v1/opportunities/discover",
                json=payload,
                headers=headers
            ) as response:
                end_time = time.time()
                response_time = end_time - start_time
                
                status = response.status
                content_type = response.headers.get('content-type', '')
                
                if 'application/json' in content_type:
                    data = await response.json()
                else:
                    data = await response.text()
                
                result = {
                    "endpoint": "/api/v1/opportunities/discover",
                    "status_code": status,
                    "response_time_seconds": round(response_time, 2),
                    "response": data,
                    "success": status == 200,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                if status == 200:
                    print(f"✅ Opportunity discovery successful: {status} ({response_time:.2f}s)")
                    if isinstance(data, dict) and 'scan_id' in data:
                        print(f"   Scan ID: {data.get('scan_id')}")
                else:
                    print(f"❌ Opportunity discovery failed: {status} ({response_time:.2f}s)")
                
                return result
        except asyncio.TimeoutError:
            print(f"⏰ Opportunity discovery timeout after 60s")
            return {
                "endpoint": "/api/v1/opportunities/discover",
                "status_code": 0,
                "error": "Timeout after 60s",
                "success": False,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            print(f"❌ Opportunity discovery error: {e}")
            return {
                "endpoint": "/api/v1/opportunities/discover",
                "status_code": 0,
                "error": str(e),
                "success": False,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run all tests and generate comprehensive report."""
        print("🚀 Starting Comprehensive Chat Endpoint Testing")
        print("=" * 80)
        print(f"🌐 Testing server: {self.base_url}")
        print(f"⏰ Test started at: {datetime.utcnow().isoformat()}")
        print("=" * 80)
        
        # Authenticate first
        auth_success = await self.authenticate()
        if not auth_success:
            print("❌ Cannot proceed without authentication")
            return {"error": "Authentication failed"}
        
        # Test endpoints
        tests = [
            self.test_health_endpoint(),
            self.test_chat_message_endpoint("Hello, what strategies do I have access to?"),
            self.test_chat_message_endpoint("Find the best opportunities now"),
            self.test_chat_message_endpoint("Show my portfolio performance"),
            self.test_portfolio_endpoint(),
            self.test_opportunity_discovery(),
        ]
        
        results = await asyncio.gather(*tests, return_exceptions=True)
        
        # Process results
        self.test_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.test_results.append({
                    "test_index": i,
                    "error": str(result),
                    "success": False
                })
            else:
                self.test_results.append(result)
        
        # Generate summary
        total_tests = len(self.test_results)
        successful_tests = len([r for r in self.test_results if r.get("success", False)])
        failed_tests = total_tests - successful_tests
        
        print("\n" + "=" * 80)
        print("📊 COMPREHENSIVE TEST RESULTS SUMMARY")
        print("=" * 80)
        
        for i, result in enumerate(self.test_results):
            status = "✅ PASS" if result.get("success", False) else "❌ FAIL"
            endpoint = result.get("endpoint", f"Test {i}")
            status_code = result.get("status_code", "N/A")
            response_time = result.get("response_time_seconds", "N/A")
            
            print(f"{status} {endpoint} - Status: {status_code} - Time: {response_time}s")
            
            if not result.get("success", False) and "error" in result:
                print(f"    Error: {result['error']}")
        
        print(f"\n🎯 OVERALL RESULTS:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Successful: {successful_tests}")
        print(f"   Failed: {failed_tests}")
        print(f"   Success Rate: {(successful_tests/total_tests)*100:.1f}%")
        
        if failed_tests == 0:
            print("\n🎉 ALL TESTS PASSED! The deployed fixes are working correctly.")
        else:
            print(f"\n⚠️  {failed_tests} tests failed. Review the detailed results above.")
        
        return {
            "summary": {
                "total_tests": total_tests,
                "successful": successful_tests,
                "failed": failed_tests,
                "success_rate": (successful_tests/total_tests)*100
            },
            "test_results": self.test_results,
            "timestamp": datetime.utcnow().isoformat()
        }


async def main():
    """Main test execution."""
    async with ChatEndpointTester() as tester:
        results = await tester.run_comprehensive_tests()
        
        # Save detailed results
        with open("chat_endpoint_test_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n📁 Detailed results saved to: chat_endpoint_test_results.json")
        
        return results["summary"]["failed"] == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)