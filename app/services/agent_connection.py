import requests
import uuid
import time
import jwt
from typing import Optional
from config.settings import settings

token = None
token_expiry = 0 
MY_DOMAIN_URL = settings.AGENTFORCE_ORG_ID
CONSUMER_KEY =  settings.CONSUMER_KEY
CONSUMER_SECRET = settings.CONSUMER_SECRET  
AGENT_ID = settings.AGENTFORCE_AGENT_ID
sequence_id = 0

def is_token_valid() -> bool:
    """Check if the token is still valid based on the expiry time in the JWT."""
    global token, token_expiry
    if token is None or token_expiry == 0:
        return False
    current_time = int(time.time())  # Current time in seconds
    return current_time < token_expiry

def create_token() -> Optional[str]:
    """Create a new OAuth2 token if the current one is invalid or expired."""
    global token, token_expiry
    if is_token_valid():
        return token

    url = f"{MY_DOMAIN_URL}/services/oauth2/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": CONSUMER_KEY,
        "client_secret": CONSUMER_SECRET
    }
    
    response = requests.post(url, data=data)
    if response.status_code != 200:
        print(f"Failed to create token: {response.status_code}")
        return None
    result = response.json()
    token = result.get("access_token")
    if not token:
        print("No access token in response")
        return None
    # Decode JWT to extract expiry time (no verification needed for exp)
    try:
        decoded_token = jwt.decode(token, options={"verify_signature": False},algorithms=["RS256"])
        token_expiry = decoded_token.get("exp", 0)
        if token_expiry == 0:
            print("No expiry time in JWT")
            return None
    except Exception:
        print("Failed to decode JWT")
        return None
    return token

def create_session_id() -> Optional[str]:
    """Create a new session ID using the Salesforce Einstein AI Agent API."""
    access_token = create_token()
    if not access_token:
        print("No valid token available")
        return None

    url = f"https://api.salesforce.com/einstein/ai-agent/v1/agents/{AGENT_ID}/sessions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    payload = {
        "externalSessionKey": str(uuid.uuid4()),
        "instanceConfig": {
            "endpoint": f"{MY_DOMAIN_URL}"
        },
        "streamingCapabilities": {
            "chunkTypes": ["Text"]
        },
        "bypassUser": True
    }

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        print(f"Failed to create session: {response.status_code}")
        return None
    result = response.json()
    return result.get("sessionId")



def send_message(session_id: str, message_text: str) -> Optional[str]:
    """Send a message to the Salesforce Einstein AI Agent and return the response message."""
    global sequence_id
    access_token = create_token()
    if not access_token:
        print("No valid token available")
        return None

    url = f"https://api.salesforce.com/einstein/ai-agent/v1/sessions/{session_id}/messages"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }
    sequence_id += 1  # Auto-increment sequence ID
    payload = {
        "message": {
            "sequenceId": sequence_id,
            "type": "Text",
            "text": message_text
        }
    }

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        print(f"Failed to send message: {response.status_code}")
        return None
    result = response.json()
    print(result)
    messages = result.get("messages", [])
    if not messages:
        print("No messages in response")
        return None
    return messages[0].get("message")