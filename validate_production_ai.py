#!/usr/bin/env python3
"""
Production AI Chat Validation Script
Tests AI chat functionality in production environment with Render Dashboard API keys.
"""

import asyncio
import json
import sys
import aiohttp
from datetime import datetime
from typing import Dict, Any
from pathlib import Path

# Add the app directory to the path using proper path resolution
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from app.core.config import get_settings
from app.services.ai_consensus_core import AIModelConnector, AIModelProvider
from app.services.ai_chat_engine import enhanced_chat_engine as chat_engine

async def test_production_ai_setup() -> Dict[str, Any]:
    """Test production AI setup with actual API keys from Render."""
    
    print("🔍 Production AI Chat Validation")
    print("=" * 50)
    
    settings = get_settings()
    results = {
        "environment": settings.ENVIRONMENT,
        "api_keys_configured": {},
        "api_connectivity": {},
        "chat_engine_test": {},
        "overall_status": "unknown",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Check API key configuration (in production these come from Render Dashboard)
    results["api_keys_configured"] = {
        "openai": bool(settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-your-")),
        "anthropic": bool(settings.ANTHROPIC_API_KEY and not settings.ANTHROPIC_API_KEY.startswith("sk-ant-your-")),
        "google": bool(settings.GOOGLE_AI_API_KEY and settings.GOOGLE_AI_API_KEY != "your-google-ai-key")
    }
    
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"Base URL: {settings.BASE_URL}")
    print("\n🔑 API Key Configuration Status:")
    
    for provider, configured in results["api_keys_configured"].items():
        if configured:
            # Show partial key for verification
            key_attr = f"{provider.upper()}_API_KEY" if provider != "google" else "GOOGLE_AI_API_KEY"
            key_value = getattr(settings, key_attr, "")
            if key_value:
                masked_key = f"{key_value[:8]}...{key_value[-4:]}" if len(key_value) > 12 else "configured"
                print(f"  ✅ {provider.upper()}: {masked_key}")
            else:
                print(f"  ❌ {provider.upper()}: Not configured")
        else:
            print(f"  ❌ {provider.upper()}: Using placeholder/not configured")
    
    # Test individual AI model connectivity
    print("\n🧪 Testing AI Model Connectivity:")
    connector = AIModelConnector()
    
    test_prompt = "This is a test message. Please respond with 'API connectivity test successful' and provide a brief analysis confidence score."
    test_context = {"test": True, "timestamp": datetime.utcnow().isoformat()}
    
    # Test each configured API
    for provider_name, configured in results["api_keys_configured"].items():
        if not configured:
            print(f"  ⏭️  {provider_name.upper()}: Skipped (not configured)")
            results["api_connectivity"][provider_name] = {"success": False, "error": "API key not configured"}
            continue
        
        try:
            if provider_name == "openai":
                provider = AIModelProvider.GPT4
            elif provider_name == "anthropic":
                provider = AIModelProvider.CLAUDE
            elif provider_name == "google":
                provider = AIModelProvider.GEMINI
            else:
                continue
            
            print(f"  🔄 Testing {provider_name.upper()}...", end="")
            response = await connector.query_ai_model(
                provider=provider,
                prompt=test_prompt,
                context=test_context
            )
            
            if response.success:
                print(f" ✅ Success (confidence: {response.confidence:.1f}, cost: ${response.cost:.4f})")
                results["api_connectivity"][provider_name] = {
                    "success": True,
                    "confidence": response.confidence,
                    "cost": response.cost,
                    "response_length": len(response.content) if response.content else 0
                }
            else:
                print(f" ❌ Failed: {response.error}")
                results["api_connectivity"][provider_name] = {
                    "success": False,
                    "error": response.error
                }
        
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            print(f" ❌ Exception: {e!s}")
            results["api_connectivity"][provider_name] = {
                "success": False,
                "error": f"Exception: {e!s}"
            }
    
    # Test the full AI chat engine
    print("\n🤖 Testing AI Chat Engine:")
    try:
        print("  🔄 Creating chat session...", end="")
        session_id = await chat_engine.start_chat_session("test_user_production")
        print(f" ✅ Session created: {session_id}")
        
        print("  🔄 Testing chat message processing...", end="")
        test_message = "Hello AI, this is a production test. Can you analyze the current crypto market sentiment?"
        
        response = await chat_engine.process_message(
            session_id=session_id,
            user_message=test_message,
            user_id="test_user_production"
        )
        
        if response.get("success"):
            print(f" ✅ Success")
            print(f"    Intent: {response.get('intent', 'unknown')}")
            print(f"    Confidence: {response.get('confidence', 0):.2f}")
            print(f"    Response length: {len(response.get('content', ''))}")
            
            results["chat_engine_test"] = {
                "success": True,
                "session_created": True,
                "message_processed": True,
                "intent": response.get('intent'),
                "confidence": response.get('confidence'),
                "response_preview": response.get('content', '')[:200] + "..." if len(response.get('content', '')) > 200 else response.get('content', '')
            }
        else:
            print(f" ❌ Failed: {response.get('error', 'Unknown error')}")
            results["chat_engine_test"] = {
                "success": False,
                "error": response.get('error', 'Unknown error')
            }
    
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as e:
        print(f" ❌ Exception: {e!s}")
        results["chat_engine_test"] = {
            "success": False,
            "error": f"Exception: {e!s}"
        }
    
    # Determine overall status
    configured_count = sum(results["api_keys_configured"].values())
    working_count = sum(1 for conn in results["api_connectivity"].values() if conn.get("success", False))
    chat_working = results["chat_engine_test"].get("success", False)
    
    if configured_count == 0:
        results["overall_status"] = "no_keys_configured"
    elif working_count == 0:
        results["overall_status"] = "keys_configured_but_not_working"
    elif not chat_working:
        results["overall_status"] = "apis_working_but_chat_broken"
    elif working_count < configured_count:
        results["overall_status"] = "partially_working"
    else:
        results["overall_status"] = "fully_working"
    
    return results

def print_production_summary(results: Dict[str, Any]):
    """Print summary of production test results."""
    
    print(f"\n📊 Production Test Summary")
    print("=" * 50)
    
    status = results["overall_status"]
    
    if status == "fully_working":
        print("🎉 SUCCESS: AI Chat is fully functional in production!")
        print("   ✅ All configured APIs are working")
        print("   ✅ Chat engine processes messages correctly")
        print("   ✅ Multi-AI consensus system is operational")
        
    elif status == "partially_working":
        print("⚠️  PARTIAL SUCCESS: AI Chat is working but with limited capability")
        working_apis = [api for api, conn in results["api_connectivity"].items() if conn.get("success")]
        print(f"   ✅ Working APIs: {', '.join(working_apis)}")
        broken_apis = [api for api, conn in results["api_connectivity"].items() if not conn.get("success")]
        if broken_apis:
            print(f"   ❌ Broken APIs: {', '.join(broken_apis)}")
        
    elif status == "apis_working_but_chat_broken":
        print("⚠️  APIs are working but chat engine has issues")
        print("   ✅ API connections successful")
        print("   ❌ Chat message processing failed")
        print("   🔧 Check chat engine configuration and error logs")
        
    elif status == "keys_configured_but_not_working":
        print("❌ FAILURE: API keys are configured but not working")
        print("   This could indicate:")
        print("   - Invalid API keys in Render Dashboard")
        print("   - Insufficient credits/quota")
        print("   - API service issues")
        print("   - Network connectivity problems")
        
    else:
        print("❌ FAILURE: No API keys configured")
        print("   Please check Render Dashboard environment variables:")
        print("   - OPENAI_API_KEY")
        print("   - ANTHROPIC_API_KEY") 
        print("   - GOOGLE_AI_API_KEY")
    
    print(f"\n📋 Test Details:")
    print(f"   Environment: {results['environment']}")
    print(f"   Configured APIs: {sum(results['api_keys_configured'].values())}/3")
    print(f"   Working APIs: {sum(1 for conn in results['api_connectivity'].values() if conn.get('success', False))}")
    print(f"   Chat Engine: {'✅ Working' if results['chat_engine_test'].get('success') else '❌ Failed'}")
    print(f"   Timestamp: {results['timestamp']}")

async def main():
    """Main production validation function."""
    try:
        results = await test_production_ai_setup()
        print_production_summary(results)
        
        # Save results to file for debugging
        with open(f"production_ai_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
            json.dump(results, f, indent=2)
        
        # Return appropriate exit code
        if results["overall_status"] in ["fully_working", "partially_working"]:
            return 0
        else:
            return 1
            
    except Exception as e:
        print(f"❌ Production test failed with exception: {e}")
        print("\nThis indicates a serious configuration or system issue.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)