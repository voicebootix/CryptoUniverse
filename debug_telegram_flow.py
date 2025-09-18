#!/usr/bin/env python3
"""Debug Telegram message flow"""

import json
import subprocess

print("=== DEBUGGING TELEGRAM MESSAGE FLOW ===")

# First, check if the webhook is actually processing messages
print("\n1. Checking webhook endpoint:")
print("   The message flow should be:")
print("   Telegram → Webhook → _process_telegram_message → _process_authenticated_message")
print("   → _process_natural_language → AI processing")

# Key code locations to check:
code_locations = {
    "Webhook Handler": "/workspace/app/api/v1/endpoints/telegram.py:253",
    "Message Processing": "/workspace/app/api/v1/endpoints/telegram.py:608", 
    "Authenticated Processing": "/workspace/app/api/v1/endpoints/telegram.py:721",
    "Natural Language Handler": "/workspace/app/api/v1/endpoints/telegram.py:813",
    "Intent Detection": "/workspace/app/api/v1/endpoints/telegram.py:824",
    "Fallback Response": "/workspace/app/api/v1/endpoints/telegram.py:854"
}

print("\n2. Code Flow Analysis:")
for location, path in code_locations.items():
    print(f"   {location}: {path}")

# Check the actual response path
print("\n3. Why 'I didn't understand' is returned:")
print("   Line 854: return '❓ I didn't understand that. Try /help for available commands.'")
print("   This happens when:")
print("   a) ai_consensus_service.analyze_opportunity returns success=False")
print("   b) An exception occurs in _process_natural_language")

print("\n4. The REAL issue:")
print("   The webhook is using app/api/v1/endpoints/telegram.py")
print("   which has its OWN _process_natural_language function")
print("   NOT the telegram_core.py MessageRouter that we connected to UnifiedChat!")

