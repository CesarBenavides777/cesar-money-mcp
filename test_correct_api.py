#!/usr/bin/env python3
"""Test correct Monarch Money API usage"""
import asyncio
import os
from dotenv import load_dotenv
from monarchmoney import MonarchMoney

load_dotenv()

async def test_correct_api():
    email = os.getenv("MONARCH_EMAIL").strip("'")
    password = os.getenv("MONARCH_PASSWORD").strip("'")
    mfa_secret = os.getenv("MONARCH_MFA_SECRET").strip("'")

    client = MonarchMoney()

    try:
        print("Authenticating...")
        await client.login(
            email=email,
            password=password,
            mfa_secret_key=mfa_secret,
            save_session=False,
            use_saved_session=False
        )
        print("✅ Authenticated")

        # The issue: get_accounts is NOT async, it returns a coroutine directly
        print("\nTrying get_accounts()...")
        result = await client.get_accounts()  # This is correct - it returns a coroutine
        accounts = result.get('accounts', [])
        print(f"✅ Found {len(accounts)} accounts")

        # Test get_transactions
        print("\nTrying get_transactions()...")
        txn_result = await client.get_transactions(limit=5)
        transactions = txn_result.get('allTransactions', {}).get('results', [])
        print(f"✅ Found {len(transactions)} transactions")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_correct_api())