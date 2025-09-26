#!/usr/bin/env python3
"""
Comprehensive test suite for all Monarch Money MCP tools
Works with OAuth authentication - no environment variables needed
"""

import asyncio
import json
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

async def test_with_oauth_credentials(email: str, password: str, mfa_secret: str = None):
    """Test all MCP tools using OAuth credentials directly"""

    # Import the OAuth-enabled server
    from fastmcp_oauth_server import mcp, store_oauth_session

    # Create a test token and store the session
    test_token = f"test_token_{datetime.now().timestamp()}"
    store_oauth_session(test_token, email, password, mfa_secret)

    # Create context with the token
    context = {'oauth_token': test_token}

    print("=" * 60)
    print("🧪 MONARCH MONEY MCP COMPREHENSIVE TEST SUITE")
    print("=" * 60)

    # Get all tools
    tools = await mcp.get_tools()
    print(f"\n✅ Found {len(tools)} tools available:")
    for tool_name in tools:
        print(f"   • {tool_name}")

    # Test results storage
    results = {}

    # Test 1: Connection Test
    print("\n" + "=" * 60)
    print("TEST 1: Connection and Authentication")
    print("-" * 60)

    if 'test_connection' in tools:
        tool = tools['test_connection']
        try:
            result = await tool.run({'context': context})
            text = extract_text_from_result(result)
            results['test_connection'] = {'status': 'PASSED', 'message': text}
            print(f"✅ {text}")
        except Exception as e:
            results['test_connection'] = {'status': 'FAILED', 'message': str(e)}
            print(f"❌ Connection test failed: {e}")

    # Test 2: Get Accounts
    print("\n" + "=" * 60)
    print("TEST 2: Get Accounts")
    print("-" * 60)

    account_id = None
    if 'get_accounts' in tools:
        tool = tools['get_accounts']
        try:
            result = await tool.run({'context': context})
            text = extract_text_from_result(result)

            # Try to extract an account ID for later tests
            lines = text.split('\n')
            for line in lines:
                if 'ID:' in line:
                    account_id = line.split('ID:')[1].strip()
                    if account_id and account_id != 'N/A':
                        break

            results['get_accounts'] = {'status': 'PASSED', 'message': text[:200] + '...'}
            print(f"✅ Accounts retrieved successfully")
            print(f"   Preview: {text[:200]}...")
            if account_id:
                print(f"   Sample Account ID: {account_id}")
        except Exception as e:
            results['get_accounts'] = {'status': 'FAILED', 'message': str(e)}
            print(f"❌ Failed to get accounts: {e}")

    # Test 3: Get Recent Transactions
    print("\n" + "=" * 60)
    print("TEST 3: Get Recent Transactions")
    print("-" * 60)

    if 'get_transactions' in tools:
        tool = tools['get_transactions']
        try:
            # Get last 30 days of transactions
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=30)

            result = await tool.run({
                'start_date': str(start_date),
                'end_date': str(end_date),
                'limit': 10,
                'context': context
            })
            text = extract_text_from_result(result)
            results['get_transactions'] = {'status': 'PASSED', 'message': text[:200] + '...'}
            print(f"✅ Transactions retrieved for {start_date} to {end_date}")
            print(f"   Preview: {text[:200]}...")
        except Exception as e:
            results['get_transactions'] = {'status': 'FAILED', 'message': str(e)}
            print(f"❌ Failed to get transactions: {e}")

    # Test 4: Get Budgets
    print("\n" + "=" * 60)
    print("TEST 4: Get Budgets")
    print("-" * 60)

    if 'get_budgets' in tools:
        tool = tools['get_budgets']
        try:
            result = await tool.run({'context': context})
            text = extract_text_from_result(result)
            results['get_budgets'] = {'status': 'PASSED', 'message': text[:200] + '...'}
            print(f"✅ Budgets retrieved successfully")
            print(f"   Preview: {text[:200]}...")
        except Exception as e:
            results['get_budgets'] = {'status': 'FAILED', 'message': str(e)}
            print(f"❌ Failed to get budgets: {e}")

    # Test 5: Get Current Month Spending Plan
    print("\n" + "=" * 60)
    print("TEST 5: Get Spending Plan (Current Month)")
    print("-" * 60)

    if 'get_spending_plan' in tools:
        tool = tools['get_spending_plan']
        try:
            current_month = datetime.now().strftime("%Y-%m")
            result = await tool.run({
                'month': current_month,
                'context': context
            })
            text = extract_text_from_result(result)
            results['get_spending_plan'] = {'status': 'PASSED', 'message': text[:200] + '...'}
            print(f"✅ Spending plan retrieved for {current_month}")
            print(f"   Preview: {text[:200]}...")
        except Exception as e:
            results['get_spending_plan'] = {'status': 'FAILED', 'message': str(e)}
            print(f"❌ Failed to get spending plan: {e}")

    # Test 6: Get Account History (if we have an account ID)
    if account_id:
        print("\n" + "=" * 60)
        print("TEST 6: Get Account History")
        print("-" * 60)

        if 'get_account_history' in tools:
            tool = tools['get_account_history']
            try:
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=90)

                result = await tool.run({
                    'account_id': account_id,
                    'start_date': str(start_date),
                    'end_date': str(end_date),
                    'context': context
                })
                text = extract_text_from_result(result)
                results['get_account_history'] = {'status': 'PASSED', 'message': text[:200] + '...'}
                print(f"✅ Account history retrieved for account {account_id}")
                print(f"   Date range: {start_date} to {end_date}")
                print(f"   Preview: {text[:200]}...")
            except Exception as e:
                results['get_account_history'] = {'status': 'FAILED', 'message': str(e)}
                print(f"❌ Failed to get account history: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for r in results.values() if r['status'] == 'PASSED')
    failed = sum(1 for r in results.values() if r['status'] == 'FAILED')

    for test_name, result in results.items():
        status_icon = "✅" if result['status'] == 'PASSED' else "❌"
        print(f"{status_icon} {test_name}: {result['status']}")

    print(f"\nTotal: {passed} passed, {failed} failed out of {len(results)} tests")

    return results

def extract_text_from_result(result):
    """Extract text from FastMCP ToolResult"""
    text = ""
    if hasattr(result, 'content') and result.content:
        for content in result.content:
            if hasattr(content, 'text'):
                text += content.text
    return text

async def test_with_env_variables():
    """Test using environment variables (backward compatibility)"""
    from fastmcp_server import mcp

    print("=" * 60)
    print("🧪 TESTING WITH ENVIRONMENT VARIABLES")
    print("=" * 60)

    tools = await mcp.get_tools()
    print(f"\n✅ Found {len(tools)} tools")

    # Test get_accounts
    if 'get_accounts' in tools:
        tool = tools['get_accounts']
        try:
            result = await tool.run({})
            text = extract_text_from_result(result)
            print(f"\nAccounts test: {text[:100]}...")
        except Exception as e:
            print(f"\n❌ Accounts test failed: {e}")

def main():
    """Main test runner with interactive mode"""
    print("\n🚀 Monarch Money MCP Test Suite")
    print("================================\n")

    # Check if credentials are provided via command line
    if len(sys.argv) >= 3:
        email = sys.argv[1]
        password = sys.argv[2]
        mfa_secret = sys.argv[3] if len(sys.argv) > 3 else None

        print(f"Using provided credentials for {email}")
        asyncio.run(test_with_oauth_credentials(email, password, mfa_secret))

    # Check for environment variables
    elif os.getenv("MONARCH_EMAIL") and os.getenv("MONARCH_PASSWORD"):
        print("Using environment variables for authentication")
        asyncio.run(test_with_env_variables())

    else:
        print("No credentials found. Please provide credentials:")
        print("\nOption 1: Command line arguments")
        print("  python test_all_tools.py <email> <password> [mfa_secret]")
        print("\nOption 2: Environment variables")
        print("  export MONARCH_EMAIL=your_email")
        print("  export MONARCH_PASSWORD=your_password")
        print("  export MONARCH_MFA_SECRET=your_mfa_secret (optional)")
        print("\nOption 3: Interactive input")

        choice = input("\nEnter credentials now? (y/n): ")
        if choice.lower() == 'y':
            email = input("Email: ")
            password = input("Password: ")
            mfa_secret = input("MFA Secret (optional, press Enter to skip): ")
            mfa_secret = mfa_secret if mfa_secret else None

            asyncio.run(test_with_oauth_credentials(email, password, mfa_secret))
        else:
            print("\nExiting. Please provide credentials and try again.")

if __name__ == "__main__":
    main()