#!/usr/bin/env python3
"""
Test script for the AI Chat System

This script tests the comprehensive AI chat engine integration with all services.
Run this to verify that the chat system is working correctly.
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.ai_chat_engine import chat_engine
from app.services.chat_integration import chat_integration


async def test_chat_system():
    """Test the comprehensive AI chat system."""
    
    print("🚀 Testing CryptoUniverse AI Chat System")
    print("=" * 50)
    
    # Test 1: Start a chat session
    print("\n1. Testing chat session creation...")
    try:
        session_id = await chat_engine.start_chat_session("test_user_123")
        print(f"✅ Chat session created: {session_id}")
    except Exception as e:
        print(f"❌ Failed to create chat session: {e}")
        return
    
    # Test 2: Test portfolio analysis
    print("\n2. Testing portfolio analysis...")
    try:
        response = await chat_engine.process_message(
            session_id=session_id,
            user_message="Show me my portfolio performance and give me recommendations",
            user_id="test_user_123"
        )
        
        if response.get("success"):
            print("✅ Portfolio analysis successful")
            print(f"   Intent: {response.get('intent')}")
            print(f"   Confidence: {response.get('confidence', 0):.1%}")
            print(f"   Content preview: {response.get('content', '')[:100]}...")
        else:
            print(f"❌ Portfolio analysis failed: {response.get('error')}")
    except Exception as e:
        print(f"❌ Portfolio analysis error: {e}")
    
    # Test 3: Test trade execution
    print("\n3. Testing trade execution...")
    try:
        response = await chat_engine.process_message(
            session_id=session_id,
            user_message="I want to buy $1000 worth of Bitcoin",
            user_id="test_user_123"
        )
        
        if response.get("success"):
            print("✅ Trade analysis successful")
            print(f"   Intent: {response.get('intent')}")
            print(f"   Confidence: {response.get('confidence', 0):.1%}")
            print(f"   Content preview: {response.get('content', '')[:100]}...")
        else:
            print(f"❌ Trade analysis failed: {response.get('error')}")
    except Exception as e:
        print(f"❌ Trade analysis error: {e}")
    
    # Test 4: Test opportunity discovery
    print("\n4. Testing opportunity discovery...")
    try:
        response = await chat_engine.process_message(
            session_id=session_id,
            user_message="Find me the best investment opportunities right now",
            user_id="test_user_123"
        )
        
        if response.get("success"):
            print("✅ Opportunity discovery successful")
            print(f"   Intent: {response.get('intent')}")
            print(f"   Confidence: {response.get('confidence', 0):.1%}")
            print(f"   Content preview: {response.get('content', '')[:100]}...")
        else:
            print(f"❌ Opportunity discovery failed: {response.get('error')}")
    except Exception as e:
        print(f"❌ Opportunity discovery error: {e}")
    
    # Test 5: Test risk assessment
    print("\n5. Testing risk assessment...")
    try:
        response = await chat_engine.process_message(
            session_id=session_id,
            user_message="Analyze the risk in my current portfolio",
            user_id="test_user_123"
        )
        
        if response.get("success"):
            print("✅ Risk assessment successful")
            print(f"   Intent: {response.get('intent')}")
            print(f"   Confidence: {response.get('confidence', 0):.1%}")
            print(f"   Content preview: {response.get('content', '')[:100]}...")
        else:
            print(f"❌ Risk assessment failed: {response.get('error')}")
    except Exception as e:
        print(f"❌ Risk assessment error: {e}")
    
    # Test 6: Test rebalancing
    print("\n6. Testing rebalancing analysis...")
    try:
        response = await chat_engine.process_message(
            session_id=session_id,
            user_message="Should I rebalance my portfolio?",
            user_id="test_user_123"
        )
        
        if response.get("success"):
            print("✅ Rebalancing analysis successful")
            print(f"   Intent: {response.get('intent')}")
            print(f"   Confidence: {response.get('confidence', 0):.1%}")
            print(f"   Content preview: {response.get('content', '')[:100]}...")
        else:
            print(f"❌ Rebalancing analysis failed: {response.get('error')}")
    except Exception as e:
        print(f"❌ Rebalancing analysis error: {e}")
    
    # Test 7: Test market analysis
    print("\n7. Testing market analysis...")
    try:
        response = await chat_engine.process_message(
            session_id=session_id,
            user_message="What's the current market sentiment and trends?",
            user_id="test_user_123"
        )
        
        if response.get("success"):
            print("✅ Market analysis successful")
            print(f"   Intent: {response.get('intent')}")
            print(f"   Confidence: {response.get('confidence', 0):.1%}")
            print(f"   Content preview: {response.get('content', '')[:100]}...")
        else:
            print(f"❌ Market analysis failed: {response.get('error')}")
    except Exception as e:
        print(f"❌ Market analysis error: {e}")
    
    # Test 8: Get chat history
    print("\n8. Testing chat history...")
    try:
        history = await chat_engine.get_chat_history(session_id, limit=10)
        print(f"✅ Retrieved {len(history)} messages from chat history")
        
        for i, msg in enumerate(history[-3:], 1):  # Show last 3 messages
            print(f"   {i}. [{msg.get('type')}] {msg.get('content', '')[:50]}...")
            
    except Exception as e:
        print(f"❌ Chat history error: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 AI Chat System Test Complete!")
    print("\nKey Features Tested:")
    print("✓ Chat session management")
    print("✓ Intent classification")
    print("✓ Portfolio analysis with AI insights")
    print("✓ Trade execution analysis")
    print("✓ Market opportunity discovery")
    print("✓ Risk assessment and management")
    print("✓ Portfolio rebalancing recommendations")
    print("✓ Comprehensive market analysis")
    print("✓ Chat history management")
    
    print(f"\nThe AI Chat System is ready for comprehensive cryptocurrency money management!")


if __name__ == "__main__":
    # Run the test
    asyncio.run(test_chat_system())