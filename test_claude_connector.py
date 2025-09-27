#!/usr/bin/env python3
"""
Test script for Claude Custom Connector
Tests the OAuth flow and MCP endpoints to ensure Claude compatibility
"""

import asyncio
import aiohttp
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_URL = "http://localhost:8000"

async def test_oauth_flow():
    """Test the OAuth flow that Claude will use"""
    async with aiohttp.ClientSession() as session:
        print("🔍 Testing OAuth Authorization Server Metadata...")

        # Test OAuth metadata endpoint
        async with session.get(f"{BASE_URL}/.well-known/oauth-authorization-server") as resp:
            if resp.status == 200:
                metadata = await resp.json()
                print("✅ OAuth metadata endpoint working")
                print(f"   Authorization URL: {metadata.get('authorization_endpoint')}")
                print(f"   Token URL: {metadata.get('token_endpoint')}")
            else:
                print(f"❌ OAuth metadata failed: {resp.status}")
                return False

        print("\n🔍 Testing OAuth Authorization...")

        # Test authorization endpoint (returns HTML form)
        async with session.get(f"{BASE_URL}/oauth/authorize") as resp:
            if resp.status == 200:
                auth_html = await resp.text()
                print("✅ OAuth authorization form working")
                print("   Authorization form rendered successfully")

                # Simulate form submission
                form_data = {
                    "action": "authorize",
                    "client_id": "test-client",
                    "code_challenge": "test_challenge",
                    "code_challenge_method": "S256",
                    "redirect_uri": "http://localhost:3000/callback",
                    "response_type": "code",
                    "scope": "claudeai"
                }

                async with session.post(f"{BASE_URL}/oauth/authorize", data=form_data, allow_redirects=False) as post_resp:
                    if post_resp.status == 302:
                        location = post_resp.headers.get('Location', '')
                        if 'code=' in location:
                            # Extract auth code from redirect URL
                            auth_code = location.split('code=')[1].split('&')[0]
                            print(f"   Generated auth code: {auth_code[:20]}...")
                        else:
                            print("❌ No authorization code in redirect")
                            return False
                    else:
                        print(f"❌ OAuth authorization submission failed: {post_resp.status}")
                        return False
            else:
                print(f"❌ OAuth authorization failed: {resp.status}")
                return False

        print("\n🔍 Testing Token Exchange...")

        # Test token exchange
        token_data = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "client_id": "test-client",
            "code_verifier": "test_verifier",  # For test challenge
            "redirect_uri": "http://localhost:3000/callback"
        }

        async with session.post(f"{BASE_URL}/oauth/token", data=token_data) as resp:
            if resp.status == 200:
                token_response = await resp.json()
                print("✅ Token exchange working")
                access_token = token_response.get('access_token')
                print(f"   Generated access token: {access_token[:20]}...")
                return access_token
            else:
                print(f"❌ Token exchange failed: {resp.status}")
                return False

async def test_mcp_endpoints(access_token):
    """Test the MCP endpoints that Claude will call"""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        print("\n🔍 Testing MCP Discovery Endpoint...")

        # Test main MCP endpoint
        async with session.get(f"{BASE_URL}/mcp") as resp:
            if resp.status == 200:
                mcp_info = await resp.json()
                print("✅ MCP discovery endpoint working")
                print(f"   Version: {mcp_info.get('version')}")
                print(f"   Capabilities: {mcp_info.get('capabilities')}")
            else:
                print(f"❌ MCP discovery failed: {resp.status}")
                return False

        print("\n🔍 Testing MCP Tools List...")

        # Test tools list
        rpc_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }

        async with session.post(f"{BASE_URL}/mcp/rpc", json=rpc_request, headers=headers) as resp:
            if resp.status == 200:
                tools_response = await resp.json()
                print("✅ Tools list working")
                tools = tools_response.get('result', {}).get('tools', [])
                print(f"   Found {len(tools)} tools:")
                for tool in tools:
                    print(f"     - {tool.get('name')}: {tool.get('description')}")
            else:
                print(f"❌ Tools list failed: {resp.status}")
                text = await resp.text()
                print(f"   Error: {text}")
                return False

        print("\n🔍 Testing MCP Tool Call (get_accounts)...")

        # Test tool call
        rpc_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "get_accounts",
                "arguments": {}
            }
        }

        async with session.post(f"{BASE_URL}/mcp/rpc", json=rpc_request, headers=headers) as resp:
            if resp.status == 200:
                call_response = await resp.json()
                print("✅ Tool call working")
                content = call_response.get('result', {}).get('content', [])
                if content:
                    result_text = content[0].get('text', '')
                    print(f"   Response preview: {result_text[:100]}...")
                else:
                    print("   No content in response")
                return True
            else:
                print(f"❌ Tool call failed: {resp.status}")
                text = await resp.text()
                print(f"   Error: {text}")
                return False

async def test_health_check():
    """Test basic server health"""
    async with aiohttp.ClientSession() as session:
        print("🔍 Testing Server Health...")
        async with session.get(f"{BASE_URL}/health") as resp:
            if resp.status == 200:
                health = await resp.json()
                print("✅ Server is healthy")
                print(f"   Status: {health.get('status')}")
                return True
            else:
                print(f"❌ Health check failed: {resp.status}")
                return False

async def main():
    """Run all tests"""
    print("🚀 Testing Claude Custom Connector Compatibility")
    print("=" * 50)

    # Check if server is running
    try:
        if not await test_health_check():
            print("\n❌ Server is not running. Start it with:")
            print("   python claude_connector_server.py")
            return

        # Test OAuth flow
        access_token = await test_oauth_flow()
        if not access_token:
            print("\n❌ OAuth flow failed - Claude won't be able to authenticate")
            return

        # Test MCP endpoints
        if await test_mcp_endpoints(access_token):
            print("\n🎉 All tests passed! Claude Custom Connector should work.")
            print("\n📋 Summary:")
            print("✅ OAuth flow working")
            print("✅ Token generation working")
            print("✅ MCP discovery working")
            print("✅ Tools list working")
            print("✅ Tool calls working")
            print("\n🚀 Ready for Claude Custom Connectors!")
        else:
            print("\n❌ MCP functionality failed")

    except aiohttp.ClientConnectorError:
        print("❌ Cannot connect to server. Make sure it's running on localhost:8000")
        print("   Start with: python claude_connector_server.py")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")

if __name__ == "__main__":
    asyncio.run(main())