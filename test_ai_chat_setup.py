#!/usr/bin/env python3
"""
AI Chat Setup Validator
Test script to validate AI chat configuration and API connectivity.
"""

import asyncio
import os
import sys
from typing import Dict, Any

# Add the app directory to the path
sys.path.append('.')

from app.core.config import get_settings
from app.services.ai_consensus_core import AIModelConnector, AIModelProvider

async def test_api_keys() -> Dict[str, Any]:
    """Test API key configuration."""
    settings = get_settings()
    
    results = {
        "api_keys_configured": {},
        "api_connectivity": {},
        "overall_status": "unknown"
    }
    
    # Check API key configuration
    results["api_keys_configured"] = {
        "openai": bool(settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-your-")),
        "anthropic": bool(settings.ANTHROPIC_API_KEY and not settings.ANTHROPIC_API_KEY.startswith("sk-ant-your-")),
        "google": bool(settings.GOOGLE_AI_API_KEY and settings.GOOGLE_AI_API_KEY != "your-google-ai-key")
    }
    
    print("🔍 API Key Configuration Status:")
    for provider, configured in results["api_keys_configured"].items():
        status = "✅ Configured" if configured else "❌ Not Configured (using placeholder)"
        print(f"  {provider.upper()}: {status}")
    
    # Test API connectivity
    connector = AIModelConnector()
    
    print("\n🧪 Testing API Connectivity:")
    
    # Test OpenAI GPT-4
    if results["api_keys_configured"]["openai"]:
        try:
            response = await connector.query_ai_model(
                provider=AIModelProvider.GPT4,
                prompt="Hello, this is a test. Please respond with 'API test successful'.",
                context={"test": True}
            )
            results["api_connectivity"]["openai"] = {
                "success": response.success,
                "error": response.error if not response.success else None
            }
            status = "✅ Working" if response.success else f"❌ Failed: {response.error}"
            print(f"  OpenAI GPT-4: {status}")
        except Exception as e:
            results["api_connectivity"]["openai"] = {"success": False, "error": str(e)}
            print(f"  OpenAI GPT-4: ❌ Exception: {str(e)}")
    else:
        results["api_connectivity"]["openai"] = {"success": False, "error": "API key not configured"}
        print(f"  OpenAI GPT-4: ⏭️  Skipped (no API key)")
    
    # Test Anthropic Claude
    if results["api_keys_configured"]["anthropic"]:
        try:
            response = await connector.query_ai_model(
                provider=AIModelProvider.CLAUDE,
                prompt="Hello, this is a test. Please respond with 'API test successful'.",
                context={"test": True}
            )
            results["api_connectivity"]["anthropic"] = {
                "success": response.success,
                "error": response.error if not response.success else None
            }
            status = "✅ Working" if response.success else f"❌ Failed: {response.error}"
            print(f"  Anthropic Claude: {status}")
        except Exception as e:
            results["api_connectivity"]["anthropic"] = {"success": False, "error": str(e)}
            print(f"  Anthropic Claude: ❌ Exception: {str(e)}")
    else:
        results["api_connectivity"]["anthropic"] = {"success": False, "error": "API key not configured"}
        print(f"  Anthropic Claude: ⏭️  Skipped (no API key)")
    
    # Test Google Gemini
    if results["api_keys_configured"]["google"]:
        try:
            response = await connector.query_ai_model(
                provider=AIModelProvider.GEMINI,
                prompt="Hello, this is a test. Please respond with 'API test successful'.",
                context={"test": True}
            )
            results["api_connectivity"]["google"] = {
                "success": response.success,
                "error": response.error if not response.success else None
            }
            status = "✅ Working" if response.success else f"❌ Failed: {response.error}"
            print(f"  Google Gemini: {status}")
        except Exception as e:
            results["api_connectivity"]["google"] = {"success": False, "error": str(e)}
            print(f"  Google Gemini: ❌ Exception: {str(e)}")
    else:
        results["api_connectivity"]["google"] = {"success": False, "error": "API key not configured"}
        print(f"  Google Gemini: ⏭️  Skipped (no API key)")
    
    # Determine overall status
    configured_count = sum(results["api_keys_configured"].values())
    working_count = sum(1 for conn in results["api_connectivity"].values() if conn["success"])
    
    if configured_count == 0:
        results["overall_status"] = "no_keys_configured"
    elif working_count == 0:
        results["overall_status"] = "keys_configured_but_not_working"
    elif working_count < configured_count:
        results["overall_status"] = "partially_working"
    else:
        results["overall_status"] = "fully_working"
    
    return results

def print_recommendations(results: Dict[str, Any]):
    """Print recommendations based on test results."""
    print("\n📋 Recommendations:")
    
    if results["overall_status"] == "no_keys_configured":
        print("❌ No API keys are properly configured.")
        print("   Please update your .env file or Render environment variables with real API keys.")
        print("   See AI_CHAT_ISSUES_AND_SOLUTIONS.md for detailed instructions.")
    
    elif results["overall_status"] == "keys_configured_but_not_working":
        print("⚠️  API keys are configured but not working.")
        print("   This could be due to:")
        print("   - Invalid API keys")
        print("   - Insufficient credits/quota")
        print("   - Network connectivity issues")
        print("   - API service downtime")
    
    elif results["overall_status"] == "partially_working":
        print("⚠️  Some APIs are working, but not all.")
        print("   The chat will work but with limited AI model diversity.")
        working_apis = [api for api, conn in results["api_connectivity"].items() if conn["success"]]
        print(f"   Working APIs: {', '.join(working_apis)}")
    
    else:
        print("✅ All configured APIs are working!")
        print("   Your AI chat should be fully functional.")
    
    print("\n🔗 Helpful Links:")
    print("   - OpenAI API Keys: https://platform.openai.com/api-keys")
    print("   - Anthropic API Keys: https://console.anthropic.com/")
    print("   - Google AI API Keys: https://aistudio.google.com/app/apikey")

async def main():
    """Main test function."""
    print("🚀 AI Chat Setup Validator")
    print("=" * 50)
    
    try:
        results = await test_api_keys()
        print_recommendations(results)
        
        print(f"\n📊 Overall Status: {results['overall_status'].replace('_', ' ').title()}")
        
        # Return appropriate exit code
        if results["overall_status"] in ["fully_working", "partially_working"]:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        print("\nThis might indicate a configuration or import issue.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())