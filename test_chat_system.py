import json
import requests
from datetime import datetime

def test_send_message_without_session_id():
    # First, login to get a valid token
    login_url = "https://cryptouniverse.onrender.com/api/v1/auth/login"
    login_data = {
        "email": "test@cryptouniverse.com",
        "password": "TestPassword123!"
    }
    
    login_response = requests.post(login_url, json=login_data)
    if login_response.status_code != 200:
        raise Exception(f"Login failed: {login_response.text}")
    
    token_data = login_response.json()
    access_token = token_data["access_token"]
    
    # Now send the chat message with valid token
    url = "https://cryptouniverse.onrender.com/api/v1/chat/message"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "message": "What's the market outlook for Bitcoin?"
    }
    
    response = requests.post(url, headers=headers, json=payload)
    print("Response Status Code:", response.status_code)
    print("Response Body:", response.text)
    
    # Basic check of the response
    assert response.status_code in [200, 201], f"Expected status code 200 or 201, but got {response.status_code}"

if __name__ == "__main__":
    test_send_message_without_session_id()