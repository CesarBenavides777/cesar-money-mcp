#!/usr/bin/env python3
"""
Test script to verify OAuth endpoints are working
"""

import json
from api.oauth_working import handler

def test_oauth_endpoints():
    """Test all OAuth endpoints"""

    # Test registration endpoint
    print("Testing OAuth registration...")
    event = {
        "httpMethod": "GET",
        "path": "/oauth/register"
    }
    response = handler(event, {})
    print(f"Registration response: {response['statusCode']}")
    if response['statusCode'] == 200:
        print(f"Body: {response['body']}")

    # Test authorization endpoint
    print("\nTesting OAuth authorization...")
    event = {
        "httpMethod": "GET",
        "path": "/oauth/authorize"
    }
    response = handler(event, {})
    print(f"Authorization response: {response['statusCode']}")
    if response['statusCode'] == 302:
        print(f"Redirect: {response['headers']['Location']}")

    # Test token endpoint
    print("\nTesting OAuth token...")
    event = {
        "httpMethod": "POST",
        "path": "/oauth/token"
    }
    response = handler(event, {})
    print(f"Token response: {response['statusCode']}")
    if response['statusCode'] == 200:
        print(f"Body: {response['body']}")

if __name__ == "__main__":
    test_oauth_endpoints()