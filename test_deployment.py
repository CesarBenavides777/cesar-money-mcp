#!/usr/bin/env python3
"""
Test script to verify deployed server compatibility with Claude Custom Connectors
Tests against your actual deployment URL to identify authentication issues
"""

import asyncio
import aiohttp
import json

# Test against your actual deployment
DEPLOYMENT_URL = "https://cesar-money-mcp.vercel.app"

async def test_deployed_oauth_flow():
    """Test the OAuth flow against the deployed server"""
    async with aiohttp.ClientSession() as session:
        print("🚀 Testing Deployed Claude Custom Connector Compatibility")
        print("=" * 60)
        print(f"Testing URL: {DEPLOYMENT_URL}")
        print()

        print("🔍 Testing Server Health...")
        try:
            async with session.get(f"{DEPLOYMENT_URL}/health") as resp:
                if resp.status == 200:
                    health = await resp.json()
                    print("✅ Server is healthy")
                    print(f"   Status: {health.get('status')}")
                else:
                    print(f"❌ Health check failed: {resp.status}")
                    return False
        except Exception as e:
            print(f"❌ Cannot connect to server: {e}")
            return False

        print("\n🔍 Testing OAuth Authorization Server Metadata...")
        try:
            async with session.get(f"{DEPLOYMENT_URL}/.well-known/oauth-authorization-server") as resp:
                print(f"Status: {resp.status}")
                if resp.status == 200:
                    metadata = await resp.json()
                    print("✅ OAuth metadata endpoint working")
                    print(f"   Authorization URL: {metadata.get('authorization_endpoint')}")
                    print(f"   Token URL: {metadata.get('token_endpoint')}")
                    print(f"   Registration URL: {metadata.get('registration_endpoint')}")
                    print(f"   Grant Types: {metadata.get('grant_types_supported')}")
                    print(f"   PKCE Methods: {metadata.get('code_challenge_methods_supported')}")
                else:
                    print(f"❌ OAuth metadata failed: {resp.status}")
                    text = await resp.text()
                    print(f"   Response: {text[:200]}...")
                    return False
        except Exception as e:
            print(f"❌ OAuth metadata error: {e}")
            return False

        print("\n🔍 Testing Dynamic Client Registration...")
        try:
            # Simulate Claude's registration request
            registration_data = {
                "client_name": "claudeai",
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
                "token_endpoint_auth_method": "none",
                "scope": "claudeai",
                "redirect_uris": ["https://claude.ai/api/mcp/auth_callback"]
            }

            async with session.post(f"{DEPLOYMENT_URL}/oauth/register", json=registration_data) as resp:
                print(f"Status: {resp.status}")
                if resp.status == 200:
                    registration_response = await resp.json()
                    print("✅ Client registration working")
                    client_id = registration_response.get('client_id')
                    print(f"   Generated client ID: {client_id}")
                    return client_id
                else:
                    print(f"❌ Client registration failed: {resp.status}")
                    text = await resp.text()
                    print(f"   Response: {text[:200]}...")
                    return False
        except Exception as e:
            print(f"❌ Client registration error: {e}")
            return False

async def test_mcp_endpoint():
    """Test the MCP endpoint structure"""
    async with aiohttp.ClientSession() as session:
        print("\n🔍 Testing MCP Discovery Endpoint...")
        try:
            async with session.get(f"{DEPLOYMENT_URL}/mcp") as resp:
                print(f"Status: {resp.status}")
                if resp.status == 200:
                    mcp_info = await resp.json()
                    print("✅ MCP discovery endpoint working")
                    print(f"   Version: {mcp_info.get('version')}")
                    print(f"   Capabilities: {mcp_info.get('capabilities')}")
                    print(f"   Server Info: {mcp_info.get('serverInfo')}")
                    print(f"   Authentication: {mcp_info.get('authentication')}")
                    return True
                else:
                    print(f"❌ MCP discovery failed: {resp.status}")
                    text = await resp.text()
                    print(f"   Response: {text[:200]}...")
                    return False
        except Exception as e:
            print(f"❌ MCP discovery error: {e}")
            return False

async def test_unauthorized_access():
    """Test that endpoints properly reject unauthorized access"""
    async with aiohttp.ClientSession() as session:
        print("\n🔍 Testing Unauthorized Access Protection...")
        try:
            # Try to access MCP RPC without authentication
            rpc_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            }

            async with session.post(f"{DEPLOYMENT_URL}/mcp/rpc", json=rpc_request) as resp:
                print(f"Status: {resp.status}")
                if resp.status == 401:
                    print("✅ Properly rejecting unauthorized requests")
                    headers = dict(resp.headers)
                    if 'WWW-Authenticate' in headers:
                        print(f"   WWW-Authenticate header: {headers['WWW-Authenticate']}")
                    else:
                        print("⚠️  Missing WWW-Authenticate header (should be present)")
                    return True
                else:
                    print(f"❌ Should return 401 but returned: {resp.status}")
                    text = await resp.text()
                    print(f"   Response: {text[:200]}...")
                    return False
        except Exception as e:
            print(f"❌ Unauthorized access test error: {e}")
            return False

async def main():
    """Run all deployment tests"""

    # Test OAuth flow
    client_id = await test_deployed_oauth_flow()
    if not client_id:
        print("\n❌ OAuth flow tests failed")
        return

    # Test MCP endpoint
    if not await test_mcp_endpoint():
        print("\n❌ MCP endpoint tests failed")
        return

    # Test security
    if not await test_unauthorized_access():
        print("\n❌ Security tests failed")
        return

    print("\n🎉 All deployment tests passed!")
    print(f"\n📋 Deployment ready for Claude Custom Connectors:")
    print(f"   URL: {DEPLOYMENT_URL}/mcp")
    print(f"   All required endpoints are working")
    print(f"   Authentication is properly configured")

if __name__ == "__main__":
    asyncio.run(main())