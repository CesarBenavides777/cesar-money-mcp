#!/usr/bin/env python3
"""
Monarch Money FastMCP Server with OAuth Support
Supports both STDIO and HTTP with true OAuth 2.0 flow
"""

import os
import asyncio
from datetime import datetime, date
from typing import List, Optional
import logging
import secrets
import json
from urllib.parse import urlencode, parse_qs

from fastmcp import FastMCP
from monarchmoney import MonarchMoney, RequireMFAException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("monarchmoney-fastmcp-oauth")

# Create the MCP server with OAuth support
mcp = FastMCP(
    "Monarch Money MCP with OAuth",
    description="Access your Monarch Money financial data with OAuth authentication"
)

# OAuth configuration
OAUTH_CLIENTS = {}  # Store registered OAuth clients
OAUTH_CODES = {}    # Store authorization codes
ACCESS_TOKENS = {}  # Store access tokens with credentials

async def get_monarch_client(email: str, password: str, mfa_secret: str = None) -> MonarchMoney:
    """Create authenticated Monarch Money client with provided credentials"""
    if not email or not password:
        raise ValueError("Monarch credentials are required")

    client = MonarchMoney()
    try:
        await client.login(
            email=email,
            password=password,
            mfa_secret_key=mfa_secret,
            save_session=False,
            use_saved_session=False
        )
        logger.info(f"Successfully authenticated with Monarch Money for {email}")
        return client
    except RequireMFAException:
        raise ValueError("MFA is required but not provided")
    except Exception as e:
        logger.error(f"Authentication failed for {email}: {e}")
        raise ValueError(f"Failed to authenticate with Monarch Money: {e}")

# OAuth Registration Endpoint
@mcp.tool
async def oauth_register(
    redirect_uris: List[str],
    client_name: str = "MCP Client",
    grant_types: List[str] = ["authorization_code"]
) -> str:
    """
    Register an OAuth client for MCP access

    Args:
        redirect_uris: List of allowed redirect URIs
        client_name: Name of the client application
        grant_types: Supported grant types

    Returns:
        JSON string with client registration details
    """
    client_id = f"mcp_{secrets.token_urlsafe(16)}"
    client_secret = secrets.token_urlsafe(32)

    OAUTH_CLIENTS[client_id] = {
        "client_secret": client_secret,
        "redirect_uris": redirect_uris,
        "client_name": client_name,
        "grant_types": grant_types
    }

    registration_response = {
        "client_id": client_id,
        "client_secret": client_secret,
        "client_name": client_name,
        "redirect_uris": redirect_uris,
        "grant_types": grant_types,
        "authorization_endpoint": "https://cesar-money-mcp.vercel.app/oauth/authorize",
        "token_endpoint": "https://cesar-money-mcp.vercel.app/oauth/token",
        "scope": "monarch:read monarch:write"
    }

    return json.dumps(registration_response, indent=2)

# OAuth Authorization
@mcp.tool
async def oauth_authorize(
    client_id: str,
    redirect_uri: str,
    monarch_email: str,
    monarch_password: str,
    monarch_mfa_secret: str = None,
    state: str = None,
    scope: str = "monarch:read monarch:write"
) -> str:
    """
    Authorize an OAuth client with Monarch Money credentials

    Args:
        client_id: OAuth client ID
        redirect_uri: Redirect URI for authorization code
        monarch_email: Monarch Money email
        monarch_password: Monarch Money password
        monarch_mfa_secret: Optional MFA secret
        state: OAuth state parameter
        scope: Requested scope

    Returns:
        Authorization code or error message
    """
    # Validate client
    if client_id not in OAUTH_CLIENTS:
        return json.dumps({"error": "invalid_client", "error_description": "Unknown client_id"})

    client = OAUTH_CLIENTS[client_id]
    if redirect_uri not in client["redirect_uris"]:
        return json.dumps({"error": "invalid_request", "error_description": "Invalid redirect_uri"})

    # Test Monarch Money credentials
    try:
        test_client = await get_monarch_client(monarch_email, monarch_password, monarch_mfa_secret)
        logger.info("Monarch credentials validated successfully")
    except Exception as e:
        return json.dumps({
            "error": "invalid_credentials",
            "error_description": f"Monarch Money authentication failed: {str(e)}"
        })

    # Generate authorization code
    auth_code = secrets.token_urlsafe(32)
    OAUTH_CODES[auth_code] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "monarch_email": monarch_email,
        "monarch_password": monarch_password,
        "monarch_mfa_secret": monarch_mfa_secret,
        "scope": scope,
        "expires_at": datetime.now().timestamp() + 600  # 10 minutes
    }

    # Return authorization response
    callback_params = {"code": auth_code}
    if state:
        callback_params["state"] = state

    callback_url = f"{redirect_uri}?{urlencode(callback_params)}"

    return json.dumps({
        "authorization_code": auth_code,
        "redirect_url": callback_url,
        "expires_in": 600,
        "message": "Authorization successful. Use the code to exchange for access token."
    })

# OAuth Token Exchange
@mcp.tool
async def oauth_token(
    grant_type: str,
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str = None
) -> str:
    """
    Exchange authorization code for access token

    Args:
        grant_type: Must be "authorization_code"
        code: Authorization code from authorize step
        client_id: OAuth client ID
        client_secret: OAuth client secret
        redirect_uri: Must match the one used in authorization

    Returns:
        JSON string with access token or error
    """
    # Validate grant type
    if grant_type != "authorization_code":
        return json.dumps({
            "error": "unsupported_grant_type",
            "error_description": "Only authorization_code grant type is supported"
        })

    # Validate client
    if client_id not in OAUTH_CLIENTS:
        return json.dumps({"error": "invalid_client", "error_description": "Unknown client_id"})

    client = OAUTH_CLIENTS[client_id]
    if client["client_secret"] != client_secret:
        return json.dumps({"error": "invalid_client", "error_description": "Invalid client_secret"})

    # Validate authorization code
    if code not in OAUTH_CODES:
        return json.dumps({"error": "invalid_grant", "error_description": "Invalid authorization code"})

    code_data = OAUTH_CODES[code]

    # Check if code expired
    if datetime.now().timestamp() > code_data["expires_at"]:
        del OAUTH_CODES[code]
        return json.dumps({"error": "invalid_grant", "error_description": "Authorization code expired"})

    # Validate redirect URI
    if redirect_uri and redirect_uri != code_data["redirect_uri"]:
        return json.dumps({"error": "invalid_grant", "error_description": "Redirect URI mismatch"})

    # Generate access token
    access_token = secrets.token_urlsafe(32)
    ACCESS_TOKENS[access_token] = {
        "client_id": client_id,
        "monarch_email": code_data["monarch_email"],
        "monarch_password": code_data["monarch_password"],
        "monarch_mfa_secret": code_data["monarch_mfa_secret"],
        "scope": code_data["scope"],
        "expires_at": datetime.now().timestamp() + 3600  # 1 hour
    }

    # Clean up authorization code
    del OAUTH_CODES[code]

    return json.dumps({
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": code_data["scope"]
    })

# Helper function to get credentials from token
async def get_credentials_from_token(access_token: str) -> tuple:
    """Extract Monarch credentials from access token"""
    if access_token not in ACCESS_TOKENS:
        raise ValueError("Invalid or expired access token")

    token_data = ACCESS_TOKENS[access_token]

    # Check if token expired
    if datetime.now().timestamp() > token_data["expires_at"]:
        del ACCESS_TOKENS[access_token]
        raise ValueError("Access token expired")

    return (
        token_data["monarch_email"],
        token_data["monarch_password"],
        token_data["monarch_mfa_secret"]
    )

# MCP Tools with OAuth token support
@mcp.tool
async def get_accounts(access_token: str = None) -> str:
    """
    Get all Monarch Money accounts with balances and details

    Args:
        access_token: OAuth access token (required for OAuth flow)
    """
    try:
        if access_token:
            email, password, mfa_secret = await get_credentials_from_token(access_token)
        else:
            # Fallback to environment variables for STDIO
            email = os.getenv("MONARCH_EMAIL")
            password = os.getenv("MONARCH_PASSWORD")
            mfa_secret = os.getenv("MONARCH_MFA_SECRET")

        client = await get_monarch_client(email, password, mfa_secret)
        result = await client.get_accounts()
        accounts = result.get('accounts', [])

        if not accounts:
            return "No accounts found."

        account_summary = f"Found {len(accounts)} accounts:\n\n"
        for account in accounts:
            name_str = account.get('displayName', 'Unknown Account')
            balance = account.get('currentBalance', 0)
            account_type = account.get('type', {}).get('display', 'Unknown')
            institution = account.get('institution', {}).get('name', 'Unknown')

            account_summary += f"📊 **{name_str}**\n"
            account_summary += f"   Balance: ${balance:,.2f}\n"
            account_summary += f"   Type: {account_type}\n"
            account_summary += f"   Institution: {institution}\n"
            account_summary += f"   ID: {account.get('id', 'N/A')}\n\n"

        return account_summary

    except Exception as e:
        error_msg = f"Error fetching accounts: {str(e)}"
        logger.error(error_msg)
        return error_msg

@mcp.tool
async def get_transactions(
    access_token: str = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    account_id: Optional[str] = None
) -> str:
    """
    Get Monarch Money transactions with optional filtering

    Args:
        access_token: OAuth access token (required for OAuth flow)
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        limit: Maximum number of transactions (default: 100, max: 500)
        account_id: Optional account ID to filter transactions
    """
    try:
        if access_token:
            email, password, mfa_secret = await get_credentials_from_token(access_token)
        else:
            email = os.getenv("MONARCH_EMAIL")
            password = os.getenv("MONARCH_PASSWORD")
            mfa_secret = os.getenv("MONARCH_MFA_SECRET")

        client = await get_monarch_client(email, password, mfa_secret)

        # Parse dates and get transactions (same logic as before)
        parsed_start = None
        parsed_end = None
        if start_date:
            parsed_start = datetime.strptime(start_date, "%Y-%m-%d").date()
        if end_date:
            parsed_end = datetime.strptime(end_date, "%Y-%m-%d").date()

        limit = min(max(1, limit), 500)

        kwargs = {
            "limit": limit,
            "start_date": parsed_start,
            "end_date": parsed_end
        }
        if account_id:
            kwargs["account_id"] = account_id

        result = await client.get_transactions(**kwargs)
        transactions = result.get('allTransactions', {}).get('results', [])

        if not transactions:
            return "No transactions found for the specified criteria."

        summary = f"Found {len(transactions)} transactions"
        if parsed_start:
            summary += f" from {start_date}"
        if parsed_end:
            summary += f" to {end_date}"
        summary += f" (showing up to {limit}):\n\n"

        for tx in transactions[:20]:
            date_str = tx.get('date', 'Unknown')
            merchant = tx.get('merchant', {}).get('name', 'Unknown Merchant')
            amount = tx.get('amount', 0)
            category = tx.get('category', {}).get('name', 'Uncategorized')
            account_name = tx.get('account', {}).get('displayName', 'Unknown Account')

            summary += f"💳 **{date_str}** - {merchant}\n"
            summary += f"   Amount: ${amount:,.2f}\n"
            summary += f"   Category: {category}\n"
            summary += f"   Account: {account_name}\n\n"

        if len(transactions) > 20:
            summary += f"... and {len(transactions) - 20} more transactions\n"

        return summary

    except Exception as e:
        error_msg = f"Error fetching transactions: {str(e)}"
        logger.error(error_msg)
        return error_msg

# Add the remaining tools with OAuth support...
@mcp.tool
async def get_budgets(access_token: str = None) -> str:
    """Get Monarch Money budget information and categories"""
    try:
        if access_token:
            email, password, mfa_secret = await get_credentials_from_token(access_token)
        else:
            email = os.getenv("MONARCH_EMAIL")
            password = os.getenv("MONARCH_PASSWORD")
            mfa_secret = os.getenv("MONARCH_MFA_SECRET")

        client = await get_monarch_client(email, password, mfa_secret)
        result = await client.get_budgets()

        if not result:
            return "No budget information available."

        budget_text = "📊 **Budget Information**\n\n"
        if isinstance(result, list):
            for budget in result:
                name = budget.get('name', 'Unnamed Budget')
                budget_text += f"Budget: {name}\n"
        else:
            budget_text += f"Budget data: {str(result)}\n"

        return budget_text

    except Exception as e:
        error_msg = f"Error fetching budgets: {str(e)}"
        logger.error(error_msg)
        return error_msg

if __name__ == "__main__":
    mcp.run()