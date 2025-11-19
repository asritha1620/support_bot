#!/usr/bin/env python3
"""
Test script to demonstrate conversation memory functionality
"""
import requests
import json
import time

# Backend URL
BASE_URL = "http://localhost:8000"

def test_conversation_memory():
    """Test conversation memory by sending multiple related messages"""

    # Test session ID
    session_id = "test_session_memory_123"

    print("🧠 Testing Conversation Memory Functionality")
    print("=" * 50)

    # First message - ask about shipping errors
    print("\n1. First message: 'What are the most common shipping errors?'")
    response1 = requests.post(f"{BASE_URL}/chat", json={
        "message": "What are the most common shipping errors?",
        "session_id": session_id
    })

    if response1.status_code == 200:
        data1 = response1.json()
        print(f"🤖 Assistant: {data1['response'][:100]}...")
    else:
        print(f"❌ Error: {response1.status_code}")
        return

    time.sleep(1)  # Small delay

    # Second message - follow up asking for more details
    print("\n2. Follow-up: 'Can you tell me more about the top 3?'")
    response2 = requests.post(f"{BASE_URL}/chat", json={
        "message": "Can you tell me more about the top 3?",
        "session_id": session_id
    })

    if response2.status_code == 200:
        data2 = response2.json()
        print(f"🤖 Assistant: {data2['response'][:100]}...")
        print("✅ Conversation memory working - assistant should reference previous context!")
    else:
        print(f"❌ Error: {response2.status_code}")

    time.sleep(1)  # Small delay

    # Third message - ask about a different topic to test context switching
    print("\n3. New topic: 'What about payment issues?'")
    response3 = requests.post(f"{BASE_URL}/chat", json={
        "message": "What about payment issues?",
        "session_id": session_id
    })

    if response3.status_code == 200:
        data3 = response3.json()
        print(f"🤖 Assistant: {data3['response'][:100]}...")
    else:
        print(f"❌ Error: {response3.status_code}")

    print("\n" + "=" * 50)
    print("🎉 Conversation memory test completed!")
    print("Check the logs to see if conversation context was included in prompts.")

if __name__ == "__main__":
    try:
        test_conversation_memory()
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend. Make sure the server is running on http://localhost:8000")
    except Exception as e:
        print(f"❌ Test failed: {e}")