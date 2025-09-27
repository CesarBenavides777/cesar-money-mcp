#!/usr/bin/env python3
"""
Final comprehensive deployment check for Claude Custom Connectors compatibility
This script validates all aspects of the deployment to ensure it will work with Claude
"""

import asyncio
import aiohttp
import json
import sys

class DeploymentChecker:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')
        self.passed_tests = 0
        self.failed_tests = 0
        self.issues = []

    def log_pass(self, test_name):
        print(f"✅ {test_name}")
        self.passed_tests += 1

    def log_fail(self, test_name, issue):
        print(f"❌ {test_name}")
        print(f"   Issue: {issue}")
        self.failed_tests += 1
        self.issues.append(f"{test_name}: {issue}")

    async def test_health(self, session):
        """Test basic server health"""
        try:
            async with session.get(f"{self.base_url}/health") as resp:
                if resp.status == 200:
                    self.log_pass("Server Health Check")
                    return True
                else:
                    self.log_fail("Server Health Check", f"HTTP {resp.status}")
                    return False
        except Exception as e:
            self.log_fail("Server Health Check", f"Connection error: {e}")
            return False

    async def test_oauth_metadata(self, session):
        """Test OAuth metadata endpoint"""
        try:
            async with session.get(f"{self.base_url}/.well-known/oauth-authorization-server") as resp:
                if resp.status == 200:
                    metadata = await resp.json()

                    # Check required fields
                    required_fields = ['authorization_endpoint', 'token_endpoint', 'registration_endpoint']
                    missing_fields = [f for f in required_fields if f not in metadata]

                    if missing_fields:
                        self.log_fail("OAuth Metadata", f"Missing fields: {missing_fields}")
                        return False

                    # Check grant types
                    grant_types = metadata.get('grant_types_supported', [])
                    if 'authorization_code' not in grant_types:
                        self.log_fail("OAuth Metadata", "Missing authorization_code grant type")
                        return False

                    if 'refresh_token' not in grant_types:
                        self.log_fail("OAuth Metadata", "Missing refresh_token grant type")
                        return False

                    # Check PKCE support
                    if 'S256' not in metadata.get('code_challenge_methods_supported', []):
                        self.log_fail("OAuth Metadata", "Missing PKCE S256 support")
                        return False

                    self.log_pass("OAuth Metadata Discovery")
                    return metadata
                else:
                    self.log_fail("OAuth Metadata", f"HTTP {resp.status}")
                    return False
        except Exception as e:
            self.log_fail("OAuth Metadata", f"Error: {e}")
            return False

    async def test_client_registration(self, session):
        """Test Dynamic Client Registration"""
        try:
            registration_data = {
                "client_name": "claudeai",
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
                "token_endpoint_auth_method": "none",
                "scope": "claudeai",
                "redirect_uris": ["https://claude.ai/api/mcp/auth_callback"]
            }

            async with session.post(f"{self.base_url}/oauth/register", json=registration_data) as resp:
                if resp.status == 200:
                    response = await resp.json()

                    # Check required response fields
                    if not response.get('client_id'):
                        self.log_fail("Client Registration", "Missing client_id in response")
                        return False

                    if response.get('client_name') != 'claudeai':
                        self.log_fail("Client Registration", "Incorrect client_name in response")
                        return False

                    self.log_pass("Dynamic Client Registration")
                    return response.get('client_id')
                else:
                    text = await resp.text()
                    self.log_fail("Client Registration", f"HTTP {resp.status}: {text[:100]}...")
                    return False
        except Exception as e:
            self.log_fail("Client Registration", f"Error: {e}")
            return False

    async def test_authorization_form(self, session, client_id):
        """Test authorization form endpoint"""
        try:
            params = {
                'response_type': 'code',
                'client_id': client_id,
                'redirect_uri': 'https://claude.ai/api/mcp/auth_callback',
                'code_challenge': 'test_challenge',
                'code_challenge_method': 'S256',
                'scope': 'claudeai'
            }

            async with session.get(f"{self.base_url}/oauth/authorize", params=params) as resp:
                if resp.status == 200:
                    content = await resp.text()
                    if 'form' in content.lower() and 'authorize' in content.lower():
                        self.log_pass("Authorization Form")
                        return True
                    else:
                        self.log_fail("Authorization Form", "Response doesn't contain HTML form")
                        return False
                else:
                    self.log_fail("Authorization Form", f"HTTP {resp.status}")
                    return False
        except Exception as e:
            self.log_fail("Authorization Form", f"Error: {e}")
            return False

    async def test_mcp_discovery(self, session):
        """Test MCP discovery endpoint"""
        try:
            async with session.get(f"{self.base_url}/mcp") as resp:
                if resp.status == 200:
                    mcp_info = await resp.json()

                    # Check required fields
                    if not mcp_info.get('version'):
                        self.log_fail("MCP Discovery", "Missing version field")
                        return False

                    if not mcp_info.get('capabilities'):
                        self.log_fail("MCP Discovery", "Missing capabilities field")
                        return False

                    if not mcp_info.get('authentication'):
                        self.log_fail("MCP Discovery", "Missing authentication field")
                        return False

                    self.log_pass("MCP Discovery Endpoint")
                    return True
                else:
                    text = await resp.text()
                    self.log_fail("MCP Discovery", f"HTTP {resp.status}: {text[:100]}...")
                    return False
        except Exception as e:
            self.log_fail("MCP Discovery", f"Error: {e}")
            return False

    async def test_unauthorized_access(self, session):
        """Test that unauthorized requests are properly rejected"""
        try:
            rpc_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {}
            }

            async with session.post(f"{self.base_url}/mcp/rpc", json=rpc_request) as resp:
                if resp.status == 401:
                    headers = dict(resp.headers)
                    if 'WWW-Authenticate' in headers:
                        self.log_pass("Unauthorized Access Protection")
                        return True
                    else:
                        self.log_fail("Unauthorized Access Protection", "Missing WWW-Authenticate header")
                        return False
                else:
                    self.log_fail("Unauthorized Access Protection", f"Expected 401, got {resp.status}")
                    return False
        except Exception as e:
            self.log_fail("Unauthorized Access Protection", f"Error: {e}")
            return False

    async def run_all_tests(self):
        """Run comprehensive deployment tests"""
        print(f"🚀 Testing deployment: {self.base_url}")
        print("=" * 60)

        async with aiohttp.ClientSession() as session:
            # Basic connectivity
            if not await self.test_health(session):
                print("\n❌ Basic connectivity failed - aborting further tests")
                return self.generate_report()

            # OAuth flow components
            metadata = await self.test_oauth_metadata(session)
            if not metadata:
                print("\n⚠️  OAuth metadata failed - some tests may not work")

            client_id = await self.test_client_registration(session)
            if not client_id:
                print("\n⚠️  Client registration failed - some tests may not work")
                client_id = "test-client"  # Use fallback for remaining tests

            await self.test_authorization_form(session, client_id)

            # MCP components
            await self.test_mcp_discovery(session)
            await self.test_unauthorized_access(session)

        return self.generate_report()

    def generate_report(self):
        """Generate final test report"""
        print("\n" + "=" * 60)
        print("📋 DEPLOYMENT TEST REPORT")
        print("=" * 60)

        print(f"✅ Passed: {self.passed_tests}")
        print(f"❌ Failed: {self.failed_tests}")

        if self.failed_tests == 0:
            print("\n🎉 All tests passed! Deployment is ready for Claude Custom Connectors!")
            print(f"   Add this URL to Claude: {self.base_url}/mcp")
            return True
        else:
            print(f"\n⚠️  {self.failed_tests} issues found. Deployment needs fixes:")
            for issue in self.issues:
                print(f"   • {issue}")

            print(f"\n💡 Next steps:")
            print(f"   1. Deploy the updated code to fix these issues")
            print(f"   2. Re-run this test script")
            print(f"   3. Once all tests pass, add {self.base_url}/mcp to Claude")
            return False

async def main():
    if len(sys.argv) != 2:
        print("Usage: python final_deployment_check.py <base_url>")
        print("Example: python final_deployment_check.py https://cesar-money-mcp.vercel.app")
        sys.exit(1)

    base_url = sys.argv[1]
    checker = DeploymentChecker(base_url)
    success = await checker.run_all_tests()

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())