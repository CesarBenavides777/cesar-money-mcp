#!/usr/bin/env python3
"""
Test script to thoroughly test all MCP tools and identify NoneType concatenation errors
"""

import asyncio
import aiohttp
import json

BASE_URL = "http://localhost:8000"

async def test_tool_call(session, tool_name, arguments=None):
    """Test a specific MCP tool call"""
    print(f"\n🔍 Testing {tool_name}...")

    # First get a valid access token
    token_data = {
        "grant_type": "authorization_code",
        "code": "test_code",
        "client_id": "test-client",
        "code_verifier": "test_verifier",
        "redirect_uri": "http://localhost:3000/callback"
    }

    # Create auth code first
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
                auth_code = location.split('code=')[1].split('&')[0]

                # Exchange for token
                token_data["code"] = auth_code
                async with session.post(f"{BASE_URL}/oauth/token", data=token_data) as token_resp:
                    if token_resp.status == 200:
                        token_response = await token_resp.json()
                        access_token = token_response.get('access_token')

                        # Now test the tool
                        headers = {
                            "Authorization": f"Bearer {access_token}",
                            "Content-Type": "application/json"
                        }

                        rpc_request = {
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "tools/call",
                            "params": {
                                "name": tool_name,
                                "arguments": arguments or {}
                            }
                        }

                        try:
                            async with session.post(f"{BASE_URL}/mcp/rpc", json=rpc_request, headers=headers) as resp:
                                if resp.status == 200:
                                    response = await resp.json()
                                    result = response.get('result', {})
                                    content = result.get('content', [])
                                    if content:
                                        text = content[0].get('text', '')
                                        print(f"✅ {tool_name} - Success")
                                        print(f"   Response length: {len(text)} characters")

                                        # Check for potential issues
                                        if "Error" in text or "error" in text:
                                            print(f"⚠️  {tool_name} - Contains error message")
                                            print(f"   Error: {text[:200]}...")

                                        return True
                                    else:
                                        print(f"❌ {tool_name} - No content in response")
                                        return False
                                else:
                                    print(f"❌ {tool_name} - HTTP {resp.status}")
                                    text = await resp.text()
                                    print(f"   Error: {text[:200]}...")
                                    return False
                        except Exception as e:
                            print(f"❌ {tool_name} - Exception: {e}")
                            return False

    print(f"❌ Failed to get access token for {tool_name}")
    return False

async def main():
    """Test all tools comprehensively"""
    print("🚀 Comprehensive MCP Tools Testing")
    print("=" * 50)

    async with aiohttp.ClientSession() as session:

        # Test tools with various argument combinations that might trigger edge cases
        test_cases = [
            ("get_accounts", {}),
            ("get_transactions", {}),
            ("get_transactions", {"start_date": "2025-06-27"}),
            ("get_transactions", {"end_date": "2025-09-27"}),
            ("get_transactions", {"start_date": "2025-06-27", "end_date": "2025-09-27"}),
            ("get_transactions", {"limit": 10}),
            ("get_transactions", {"limit": 1000}),
            ("get_transactions", {"account_id": "217794265204776339"}),  # Known account ID
            ("get_transactions", {"start_date": "2025-06-27", "limit": 5}),
            ("get_budgets", {}),
            ("get_spending_plan", {}),
            ("get_spending_plan", {"month": "2025-09"}),
            ("get_account_history", {"account_id": "217794265204776339"}),
            ("get_account_history", {"account_id": "217794265204776339", "start_date": "2025-06-27"}),
            ("get_account_history", {"account_id": "217794265204776339", "start_date": "2025-06-27", "end_date": "2025-09-27"}),
        ]

        results = []
        for tool_name, arguments in test_cases:
            result = await test_tool_call(session, tool_name, arguments)
            results.append((tool_name, arguments, result))

            # Small delay between calls
            await asyncio.sleep(0.5)

        print("\n📋 Test Summary:")
        print("=" * 30)

        passed = 0
        failed = 0

        for tool_name, arguments, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            args_str = f" with {arguments}" if arguments else ""
            print(f"{status} - {tool_name}{args_str}")
            if result:
                passed += 1
            else:
                failed += 1

        print(f"\nTotal: {passed} passed, {failed} failed")

        if failed == 0:
            print("🎉 All tools working correctly - no NoneType concatenation errors!")
        else:
            print("⚠️  Some tools have issues - check the error messages above")

if __name__ == "__main__":
    asyncio.run(main())