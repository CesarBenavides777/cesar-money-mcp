#!/usr/bin/env python3
"""Test MCP server locally"""
import json
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(__file__))

# Import the handler directly from api/mcp.py
from api.mcp import handler
from http.server import HTTPServer
import threading
import time
import requests

def run_server(port=8080):
    """Run the test server"""
    server = HTTPServer(('localhost', port), handler)
    print(f"Starting test server on port {port}")
    server.serve_forever()

def test_mcp_endpoint():
    """Test the MCP endpoint"""
    time.sleep(2)  # Give server time to start
    
    # Test tools/list
    print("\n1. Testing tools/list...")
    response = requests.post('http://localhost:8080', json={
        "jsonrpc": "2.0",
        "method": "tools/list",
        "id": 1
    })
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Tools count: {len(result.get('result', {}).get('tools', []))}")
    
    # Test tools/call with get_transactions
    print("\n2. Testing tools/call with get_transactions...")
    response = requests.post('http://localhost:8080', json={
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "get_transactions",
            "arguments": {
                "start_date": "2025-06-01",
                "end_date": "2025-08-31",
                "limit": 10
            }
        },
        "id": 2
    })
    print(f"Status: {response.status_code}")
    result = response.json()
    if 'error' in result:
        print(f"Error: {result['error']}")
    else:
        content = result.get('result', {}).get('content', [])
        if content:
            text = content[0].get('text', '')[:200]
            print(f"Result preview: {text}...")

if __name__ == "__main__":
    # Start server in background thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Run tests
    try:
        test_mcp_endpoint()
    except Exception as e:
        print(f"Test error: {e}")
    
    print("\nTests complete. Server will stop.")
