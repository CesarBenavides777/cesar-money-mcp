#!/usr/bin/env python3
"""
Monarch Money MCP Server using FastMCP
Simple and clean implementation using the FastMCP framework
"""

import os
import asyncio
from datetime import datetime, date
from typing import List, Optional
import logging

from fastmcp import FastMCP
from monarchmoney import MonarchMoney, RequireMFAException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("monarchmoney-fastmcp")

# Environment variables
MONARCH_EMAIL = os.getenv("MONARCH_EMAIL")
MONARCH_PASSWORD = os.getenv("MONARCH_PASSWORD")
MONARCH_MFA_SECRET = os.getenv("MONARCH_MFA_SECRET")

# Create the MCP server
mcp = FastMCP("Monarch Money MCP")

async def get_monarch_client() -> MonarchMoney:
    """Create authenticated Monarch Money client"""
    if not MONARCH_EMAIL or not MONARCH_PASSWORD:
        logger.error("Missing credentials - MONARCH_EMAIL or MONARCH_PASSWORD not set")
        raise ValueError("Monarch credentials not configured. Set MONARCH_EMAIL and MONARCH_PASSWORD environment variables.")

    logger.info(f"Attempting to authenticate with email: {MONARCH_EMAIL[:3]}...{MONARCH_EMAIL[-10:]}")
    logger.info(f"MFA Secret configured: {bool(MONARCH_MFA_SECRET)}")

    client = MonarchMoney()
    try:
        await client.login(
            email=MONARCH_EMAIL,
            password=MONARCH_PASSWORD,
            mfa_secret_key=MONARCH_MFA_SECRET,
            save_session=False,
            use_saved_session=False
        )
        logger.info("Successfully authenticated with Monarch Money")
        return client
    except RequireMFAException as e:
        logger.error(f"MFA required but not configured properly: {str(e)}")
        raise ValueError("MFA is required but MONARCH_MFA_SECRET is not configured")
    except Exception as e:
        logger.error(f"Authentication failed - Type: {type(e).__name__}, Message: {str(e)}")
        logger.error(f"Full error details: {repr(e)}")
        raise ValueError(f"Failed to authenticate with Monarch Money: {e}")

@mcp.tool
async def get_accounts() -> str:
    """Get all Monarch Money accounts with balances and details"""
    try:
        logger.info("Starting get_accounts request")
        client = await get_monarch_client()
        logger.info("Client authenticated, fetching accounts...")

        result = await client.get_accounts()
        logger.info(f"Raw API response type: {type(result)}")
        logger.info(f"Raw API response keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")

        accounts = result.get('accounts', [])
        logger.info(f"Found {len(accounts)} accounts in response")

        if not accounts:
            logger.warning("No accounts found in API response")
            return "No accounts found."

        account_summary = f"Found {len(accounts)} accounts:\n\n"
        for i, account in enumerate(accounts):
            logger.debug(f"Processing account {i+1}: {account.get('displayName', 'Unknown')}")
            name_str = account.get('displayName', 'Unknown Account')
            balance = account.get('currentBalance', 0)
            account_type = account.get('type', {}).get('display', 'Unknown')
            institution = account.get('institution', {}).get('name', 'Unknown')

            account_summary += f"📊 **{name_str}**\n"
            account_summary += f"   Balance: ${balance:,.2f}\n"
            account_summary += f"   Type: {account_type}\n"
            account_summary += f"   Institution: {institution}\n"
            account_summary += f"   ID: {account.get('id', 'N/A')}\n\n"

        logger.info("Successfully processed accounts data")
        return account_summary

    except Exception as e:
        error_msg = f"Error fetching accounts: {str(e)}"
        logger.error(f"get_accounts failed - Type: {type(e).__name__}, Message: {str(e)}")
        logger.error(f"Full error details: {repr(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return error_msg

@mcp.tool
async def get_transactions(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    account_id: Optional[str] = None
) -> str:
    """
    Get Monarch Money transactions with optional filtering

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        limit: Maximum number of transactions (default: 100, max: 500)
        account_id: Optional account ID to filter transactions
    """
    try:
        client = await get_monarch_client()

        # Parse dates if provided
        parsed_start = None
        parsed_end = None
        if start_date:
            try:
                parsed_start = datetime.strptime(start_date, "%Y-%m-%d").date()
                logger.info(f"Parsed start_date: {parsed_start}")
            except ValueError as e:
                logger.error(f"Invalid start_date format '{start_date}': {e}")
                return f"Invalid start_date format. Use YYYY-MM-DD format."

        if end_date:
            try:
                parsed_end = datetime.strptime(end_date, "%Y-%m-%d").date()
                logger.info(f"Parsed end_date: {parsed_end}")
            except ValueError as e:
                logger.error(f"Invalid end_date format '{end_date}': {e}")
                return f"Invalid end_date format. Use YYYY-MM-DD format."

        # Limit to reasonable bounds
        limit = min(max(1, limit), 500)
        logger.info(f"Using limit: {limit}")

        # Get transactions - convert dates to strings to avoid serialization issues
        kwargs = {"limit": limit}
        if parsed_start:
            # Convert date object to string for API compatibility
            kwargs["start_date"] = parsed_start.isoformat()
            logger.info(f"Converted start_date to string: {kwargs['start_date']}")
        if parsed_end:
            # Convert date object to string for API compatibility
            kwargs["end_date"] = parsed_end.isoformat()
            logger.info(f"Converted end_date to string: {kwargs['end_date']}")
        if account_id:
            kwargs["account_id"] = account_id

        logger.info(f"Calling get_transactions with kwargs: {kwargs}")
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

        for tx in transactions[:20]:  # Show first 20 for readability
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
        logger.error(f"get_transactions failed - Type: {type(e).__name__}, Message: {str(e)}")
        logger.error(f"Full error details: {repr(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return error_msg

@mcp.tool
async def get_budgets() -> str:
    """Get Monarch Money budget information and categories"""
    try:
        client = await get_monarch_client()
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

@mcp.tool
async def get_spending_plan(month: Optional[str] = None) -> str:
    """
    Get spending plan for a specific month

    Args:
        month: Month in YYYY-MM format (defaults to current month)
    """
    try:
        client = await get_monarch_client()

        if month:
            # Parse YYYY-MM format
            year, month_num = map(int, month.split('-'))
            start_date = date(year, month_num, 1)
            if month_num == 12:
                end_date = date(year + 1, 1, 1)
            else:
                end_date = date(year, month_num + 1, 1)
        else:
            # Use current month
            now = datetime.now()
            start_date = date(now.year, now.month, 1)
            if now.month == 12:
                end_date = date(now.year + 1, 1, 1)
            else:
                end_date = date(now.year, now.month + 1, 1)

        result = await client.get_spending_plan(start_date=start_date.isoformat(), end_date=end_date.isoformat())

        plan_text = f"📈 **Spending Plan for {start_date.strftime('%Y-%m')}**\n\n"
        plan_text += f"Plan data: {str(result)}\n"

        return plan_text

    except Exception as e:
        error_msg = f"Error fetching spending plan: {str(e)}"
        logger.error(error_msg)
        return error_msg

@mcp.tool
async def get_account_history(
    account_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> str:
    """
    Get balance history for a specific account

    Args:
        account_id: Account ID to get history for
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    """
    try:
        client = await get_monarch_client()

        # Parse dates if provided
        parsed_start = None
        parsed_end = None
        if start_date:
            parsed_start = datetime.strptime(start_date, "%Y-%m-%d").date()
        if end_date:
            parsed_end = datetime.strptime(end_date, "%Y-%m-%d").date()

        result = await client.get_account_history(
            account_id=account_id,
            start_date=parsed_start.isoformat() if parsed_start else None,
            end_date=parsed_end.isoformat() if parsed_end else None
        )

        if not result:
            return f"No history found for account {account_id}"

        history_text = f"📊 **Account History for {account_id}**\n\n"
        history_text += f"History data: {str(result)}\n"

        return history_text

    except Exception as e:
        error_msg = f"Error fetching account history: {str(e)}"
        logger.error(error_msg)
        return error_msg

if __name__ == "__main__":
    mcp.run()