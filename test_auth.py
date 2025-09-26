#!/usr/bin/env python3
"""Test Monarch Money authentication"""
import asyncio
import os
from dotenv import load_dotenv
from monarchmoney import MonarchMoney

# Load .env file
load_dotenv()

async def test_auth():
    email = os.getenv("MONARCH_EMAIL")
    password = os.getenv("MONARCH_PASSWORD")
    mfa_secret = os.getenv("MONARCH_MFA_SECRET")

    # Remove quotes if present
    if email and email.startswith("'"):
        email = email.strip("'")
    if password and password.startswith("'"):
        password = password.strip("'")
    if mfa_secret and mfa_secret.startswith("'"):
        mfa_secret = mfa_secret.strip("'")

    print(f"Testing authentication for: {email}")
    print(f"Password length: {len(password) if password else 0}")
    print(f"MFA Secret provided: {bool(mfa_secret)}")

    client = MonarchMoney()

    try:
        print("\nAttempting login...")
        await client.login(
            email=email,
            password=password,
            mfa_secret_key=mfa_secret,
            save_session=False,
            use_saved_session=False
        )
        print("✅ Authentication successful!")

        # Try to get accounts
        print("\nFetching accounts...")
        result = await client.get_accounts()
        accounts = result.get('accounts', [])
        print(f"✅ Found {len(accounts)} accounts")

        for account in accounts[:3]:  # Show first 3
            print(f"  - {account.get('displayName', 'Unknown')}: ${account.get('currentBalance', 0):,.2f}")

    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        print(f"Error type: {type(e).__name__}")

if __name__ == "__main__":
    asyncio.run(test_auth())