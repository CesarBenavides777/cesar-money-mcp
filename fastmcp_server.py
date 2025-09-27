#!/usr/bin/env python3
"""
MCP-Compliant Monarch Money Server
Implements MCP Protocol Version 2025-06-18 specification
Compatible with Claude Custom Connectors and remote MCP servers
"""

import os
import sys
import asyncio
import logging
import traceback
from datetime import datetime, date
from typing import List, Optional, Dict, Any, Union
from pathlib import Path

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not available, use system env vars

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("monarchmoney-mcp")

try:
    from mcp.server import FastMCP
    from monarchmoney import MonarchMoney, RequireMFAException
    from pydantic import BaseModel, Field, validator

except ImportError as e:
    logger.error(f"Required dependencies not found: {e}")
    logger.error("Please install: pip install mcp monarchmoney pydantic")
    sys.exit(1)

# Environment configuration with secure defaults
class Config:
    """Secure configuration management following MCP best practices"""

    def __init__(self):
        # Required credentials - fail fast if not provided
        self.monarch_email = os.getenv("MONARCH_EMAIL")
        self.monarch_password = os.getenv("MONARCH_PASSWORD")

        # Optional MFA secret
        self.monarch_mfa_secret = os.getenv("MONARCH_MFA_SECRET")

        # Server configuration
        self.server_name = os.getenv("MCP_SERVER_NAME", "Monarch Money MCP Server")
        self.server_version = os.getenv("MCP_SERVER_VERSION", "1.0.0")
        self.protocol_version = "2025-06-18"

        # OAuth configuration (if available)
        self.oauth_client_id = os.getenv("OAUTH_CLIENT_ID")
        self.oauth_client_secret = os.getenv("OAUTH_CLIENT_SECRET")

        # Validate required configuration
        self._validate()

    def _validate(self):
        """Validate configuration and provide helpful error messages"""
        if not self.monarch_email or not self.monarch_password:
            logger.error("Missing required environment variables:")
            logger.error("- MONARCH_EMAIL: Your Monarch Money account email")
            logger.error("- MONARCH_PASSWORD: Your Monarch Money account password")
            logger.error("- MONARCH_MFA_SECRET: (Optional) Your MFA secret key")
            raise ValueError("Required Monarch Money credentials not configured")

        logger.info(f"Configuration loaded for: {self.monarch_email[:3]}...{self.monarch_email[-10:]}")
        logger.info(f"MFA enabled: {bool(self.monarch_mfa_secret)}")

# Global configuration
config = Config()

# Pydantic models for type safety and validation
class GetTransactionsRequest(BaseModel):
    """Request model for get_transactions tool"""
    start_date: Optional[str] = Field(None, description="Start date in YYYY-MM-DD format")
    end_date: Optional[str] = Field(None, description="End date in YYYY-MM-DD format")
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of transactions")
    account_id: Optional[str] = Field(None, description="Optional account ID filter")

    @validator('start_date', 'end_date')
    def validate_date_format(cls, v):
        if v is not None:
            try:
                datetime.strptime(v, "%Y-%m-%d")
            except ValueError:
                raise ValueError("Date must be in YYYY-MM-DD format")
        return v

class GetAccountHistoryRequest(BaseModel):
    """Request model for get_account_history tool"""
    account_id: str = Field(..., description="Account ID to get history for")
    start_date: Optional[str] = Field(None, description="Start date in YYYY-MM-DD format")
    end_date: Optional[str] = Field(None, description="End date in YYYY-MM-DD format")

class GetSpendingPlanRequest(BaseModel):
    """Request model for get_spending_plan tool"""
    month: Optional[str] = Field(None, description="Month in YYYY-MM format")

# Create the MCP server using FastMCP for compatibility
mcp = FastMCP("Monarch Money MCP Server")

def safe_str(value, default="Unknown"):
    """Ultra-safe string conversion that handles None, empty, and complex objects"""
    if value is None:
        return str(default)
    if isinstance(value, str):
        return value if value.strip() else str(default)
    try:
        result = str(value)
        return result if result.strip() else str(default)
    except (TypeError, ValueError):
        return str(default)

def safe_dict_get(obj, key, default="Unknown"):
    """Safely get a value from a dictionary-like object"""
    if not isinstance(obj, dict):
        return str(default)
    value = obj.get(key)
    return safe_str(value, default)

async def get_monarch_client() -> MonarchMoney:
    """Get authenticated Monarch Money client with proper error handling"""
    try:
        client = MonarchMoney()

        login_kwargs = {
            "email": config.monarch_email,
            "password": config.monarch_password,
            "save_session": False,
            "use_saved_session": False
        }

        if config.monarch_mfa_secret:
            login_kwargs["mfa_secret_key"] = config.monarch_mfa_secret

        await client.login(**login_kwargs)
        logger.info("Successfully authenticated with Monarch Money")
        return client

    except RequireMFAException as e:
        logger.error(f"MFA required but not configured: {e}")
        raise ValueError("MFA is required but MONARCH_MFA_SECRET is not configured")
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise ValueError(f"Failed to authenticate with Monarch Money: {str(e)}")

@mcp.tool()
async def get_accounts() -> str:
    """Get all Monarch Money accounts with balances and details. Returns comprehensive account information including current balances, account types, and institution details."""
    try:
        client = await get_monarch_client()
        result = await client.get_accounts()
        accounts = result.get('accounts', [])

        if not accounts:
            return "No accounts found."

        account_summary = f"Found {len(accounts)} accounts:\n\n"

        for account in accounts:
            # Ultra-safe string extraction using helper functions
            name_str = safe_str(account.get('displayName'), 'Unknown Account')
            balance = account.get('currentBalance') if account.get('currentBalance') is not None else 0
            account_type = safe_dict_get(account.get('type'), 'display', 'Unknown')
            institution = safe_dict_get(account.get('institution'), 'name', 'Unknown')
            account_id = safe_str(account.get('id'), 'N/A')

            account_summary += f"📊 **{name_str}**\n"
            account_summary += f"   Balance: ${balance:,.2f}\n"
            account_summary += f"   Type: {account_type}\n"
            account_summary += f"   Institution: {institution}\n"
            account_summary += f"   ID: {account_id}\n\n"

        return account_summary

    except Exception as e:
        logger.error(f"Error in get_accounts: {e}")
        return f"Error fetching accounts: {str(e)}"

@mcp.tool()
async def get_transactions(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    account_id: Optional[str] = None
) -> str:
    """Get Monarch Money transactions with optional filtering. Supports date range filtering, account-specific queries, and pagination.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        limit: Maximum number of transactions (1-1000)
        account_id: Optional account ID to filter transactions
    """
    try:
        client = await get_monarch_client()

        # Build query parameters
        kwargs = {"limit": min(max(1, limit), 1000)}

        if start_date:
            try:
                parsed_start = datetime.strptime(start_date, "%Y-%m-%d").date()
                kwargs["start_date"] = parsed_start.isoformat()
            except ValueError:
                return "Invalid start_date format. Use YYYY-MM-DD format."

        if end_date:
            try:
                parsed_end = datetime.strptime(end_date, "%Y-%m-%d").date()
                kwargs["end_date"] = parsed_end.isoformat()
            except ValueError:
                return "Invalid end_date format. Use YYYY-MM-DD format."

        if account_id:
            kwargs["account_id"] = account_id

        result = await client.get_transactions(**kwargs)
        transactions = result.get('allTransactions', {}).get('results', [])

        if not transactions:
            return "No transactions found for the specified criteria."

        summary = f"Found {len(transactions)} transactions"
        if start_date:
            summary += f" from {safe_str(start_date, 'Unknown')}"
        if end_date:
            summary += f" to {safe_str(end_date, 'Unknown')}"
        summary += f" (showing up to {limit}):\n\n"

        # Show first 20 transactions for readability
        for tx in transactions[:20]:
            # Ultra-safe string extraction using helper functions
            date_str = safe_str(tx.get('date'), 'Unknown')
            merchant = safe_dict_get(tx.get('merchant'), 'name', 'Unknown Merchant')
            amount = tx.get('amount') if tx.get('amount') is not None else 0
            category = safe_dict_get(tx.get('category'), 'name', 'Uncategorized')
            account_name = safe_dict_get(tx.get('account'), 'displayName', 'Unknown Account')

            summary += f"💳 **{date_str}** - {merchant}\n"
            summary += f"   Amount: ${amount:,.2f}\n"
            summary += f"   Category: {category}\n"
            summary += f"   Account: {account_name}\n\n"

        if len(transactions) > 20:
            summary += f"... and {len(transactions) - 20} more transactions\n"

        return summary

    except Exception as e:
        logger.error(f"Error in get_transactions: {e}")
        return f"Error fetching transactions: {str(e)}"

@mcp.tool()
async def get_budgets() -> str:
    """Get Monarch Money budget information and categories. Returns budget data and spending categories."""
    try:
        client = await get_monarch_client()
        result = await client.get_budgets()

        if not result:
            return "No budget information available."

        budget_text = "📊 **Budget Information**\n\n"

        if isinstance(result, list):
            for budget in result:
                # Ultra-safe string extraction using helper functions
                name = safe_str(budget.get('name'), 'Unnamed Budget')
                budget_text += f"Budget: {name}\n"
        else:
            budget_text += f"Budget data: {safe_str(result, 'No data')}\n"

        return budget_text

    except Exception as e:
        logger.error(f"Error in get_budgets: {e}")
        return f"Error fetching budgets: {str(e)}"

@mcp.tool()
async def get_spending_plan(month: Optional[str] = None) -> str:
    """Get spending plan for a specific month. Returns detailed spending plan information and budget allocations.

    Args:
        month: Month in YYYY-MM format (defaults to current month)
    """
    try:
        client = await get_monarch_client()

        if month:
            try:
                # Parse YYYY-MM format
                year, month_num = map(int, month.split('-'))
                start_date = date(year, month_num, 1)
                if month_num == 12:
                    end_date = date(year + 1, 1, 1)
                else:
                    end_date = date(year, month_num + 1, 1)
            except ValueError:
                return "Invalid month format. Use YYYY-MM format."
        else:
            # Use current month
            now = datetime.now()
            start_date = date(now.year, now.month, 1)
            if now.month == 12:
                end_date = date(now.year + 1, 1, 1)
            else:
                end_date = date(now.year, now.month + 1, 1)

        result = await client.get_spending_plan(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat()
        )

        plan_text = f"📈 **Spending Plan for {start_date.strftime('%Y-%m')}**\n\n"
        plan_text += f"Plan data: {str(result)}\n"

        return plan_text

    except Exception as e:
        logger.error(f"Error in get_spending_plan: {e}")
        return f"Error fetching spending plan: {str(e)}"

@mcp.tool()
async def get_account_history(
    account_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> str:
    """Get balance history for a specific account. Returns historical balance data over time.

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
            try:
                parsed_start = datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError:
                return "Invalid start_date format. Use YYYY-MM-DD format."

        if end_date:
            try:
                parsed_end = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                return "Invalid end_date format. Use YYYY-MM-DD format."

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
        logger.error(f"Error in get_account_history: {e}")
        return f"Error fetching account history: {str(e)}"

if __name__ == "__main__":
    logger.info("Starting Monarch Money MCP Server")
    logger.info(f"Protocol version: {config.protocol_version}")
    logger.info("Server is now MCP 2025-06-18 specification compliant")
    logger.info("Compatible with Claude Custom Connectors")
    mcp.run()