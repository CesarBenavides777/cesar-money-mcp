import requests
import json

BASE_URL = "https://cesar-money-f8a61xxa4-csar-e-benavides-projects.vercel.app"

print("Testing Monarch Money MCP Deployment")
print("=" * 50)

# Test 1: MCP Discovery
print("\n1. Testing MCP Discovery endpoint...")
response = requests.get(f"{BASE_URL}/.well-known/mcp")
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"   Server: {data.get('name', 'Unknown')}")
    print(f"   Tools available: {len(data.get('capabilities', {}).get('tools', []))}")

# Test 2: Tools List
print("\n2. Testing tools/list...")
response = requests.post(f"{BASE_URL}/mcp", json={
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 1
})
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    if 'result' in data:
        tools = data['result'].get('tools', [])
        print(f"   Found {len(tools)} tools:")
        for tool in tools[:3]:
            print(f"      - {tool['name']}")

# Test 3: Get Accounts (should work with env vars)
print("\n3. Testing get_accounts...")
response = requests.post(f"{BASE_URL}/mcp", json={
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "get_accounts",
        "arguments": {}
    },
    "id": 2
})
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    if 'error' in data:
        print(f"   Error: {data['error'].get('message', 'Unknown error')}")
    elif 'result' in data:
        content = data['result'].get('content', [])
        if content:
            text = content[0].get('text', '')
            print(f"   Success: {text[:100]}...")

# Test 4: Get Transactions
print("\n4. Testing get_transactions...")
response = requests.post(f"{BASE_URL}/mcp", json={
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "get_transactions",
        "arguments": {
            "start_date": "2025-01-01",
            "end_date": "2025-01-31",
            "limit": 5
        }
    },
    "id": 3
})
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    if 'error' in data:
        print(f"   Error: {data['error'].get('message', 'Unknown error')}")
    elif 'result' in data:
        content = data['result'].get('content', [])
        if content:
            text = content[0].get('text', '')
            print(f"   Success: {text[:100]}...")

print("\n" + "=" * 50)
print("Deployment test complete!")
