#!/usr/bin/env python3
"""
Monarch Money MCP Server
Official MCP SDK implementation for Anthropic's Model Context Protocol
"""

import asyncio
import os
import sys
from typing import Any, Sequence
import logging

# MCP SDK imports
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio

# Monarch Money imports
from monarchmoney import MonarchMoney, RequireMFAException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("monarchmoney-mcp")

# Environment variables
MONARCH_EMAIL = os.getenv("MONARCH_EMAIL")
MONARCH_PASSWORD = os.getenv("MONARCH_PASSWORD")
MONARCH_MFA_SECRET = os.getenv("MONARCH_MFA_SECRET")

# Create the server instance
server = Server("monarchmoney-mcp")

async def get_monarch_client() -> MonarchMoney:
    """Create authenticated Monarch Money client"""
    if not MONARCH_EMAIL or not MONARCH_PASSWORD:
        raise ValueError("Monarch credentials not configured. Set MONARCH_EMAIL and MONARCH_PASSWORD environment variables.")

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
    except RequireMFAException:
        raise ValueError("MFA is required but MONARCH_MFA_SECRET is not configured")
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise ValueError(f"Failed to authenticate with Monarch Money: {e}")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available MCP tools"""
    return [
        types.Tool(
            name="get_accounts",
            description="Get all Monarch Money accounts with balances and details",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="get_transactions",
            description="Get Monarch Money transactions with optional date filtering",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of transactions to return (default: 100, max: 500)",
                        "minimum": 1,
                        "maximum": 500
                    },
                    "account_id": {
                        "type": "string",
                        "description": "Optional account ID to filter transactions"
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="get_budgets",
            description="Get Monarch Money budget information and categories",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="get_spending_plan",
            description="Get current month's spending plan with categories and limits",
            inputSchema={
                "type": "object",
                "properties": {
                    "month": {
                        "type": "string",
                        "description": "Month in YYYY-MM format (defaults to current month)"
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="get_account_history",
            description="Get balance history for a specific account",
            inputSchema={
                "type": "object",
                "properties": {
                    "account_id": {
                        "type": "string",
                        "description": "Account ID to get history for"
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format"
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format"
                    }
                },
                "required": ["account_id"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any] | None) -> list[types.TextContent]:
    """Handle tool execution"""
    if arguments is None:
        arguments = {}

    try:
        client = await get_monarch_client()

        if name == "get_accounts":
            result = await client.get_accounts()
            accounts = result.get('accounts', [])

            if not accounts:
                return [types.TextContent(
                    type="text",
                    text="No accounts found."
                )]

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

            return [types.TextContent(type="text", text=account_summary)]

        elif name == "get_transactions":
            from datetime import datetime, date

            start_date = arguments.get("start_date")
            end_date = arguments.get("end_date")
            limit = min(int(arguments.get("limit", 100)), 500)
            account_id = arguments.get("account_id")

            # Parse dates if provided
            parsed_start = None
            parsed_end = None
            if start_date:
                parsed_start = datetime.strptime(start_date, "%Y-%m-%d").date()
            if end_date:
                parsed_end = datetime.strptime(end_date, "%Y-%m-%d").date()

            # Get transactions
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
                return [types.TextContent(
                    type="text",
                    text="No transactions found for the specified criteria."
                )]

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

            return [types.TextContent(type="text", text=summary)]

        elif name == "get_budgets":
            result = await client.get_budgets()

            if not result:
                return [types.TextContent(
                    type="text",
                    text="No budget information available."
                )]

            budget_text = "📊 **Budget Information**\n\n"

            if isinstance(result, list):
                for budget in result:
                    name = budget.get('name', 'Unnamed Budget')
                    budget_text += f"Budget: {name}\n"
                    # Add more budget details as available
            else:
                budget_text += f"Budget data: {str(result)}\n"

            return [types.TextContent(type="text", text=budget_text)]

        elif name == "get_spending_plan":
            from datetime import datetime

            month_str = arguments.get("month")
            if month_str:
                # Parse YYYY-MM format
                year, month = map(int, month_str.split('-'))
                start_date = date(year, month, 1)
                if month == 12:
                    end_date = date(year + 1, 1, 1)
                else:
                    end_date = date(year, month + 1, 1)
            else:
                # Use current month
                now = datetime.now()
                start_date = date(now.year, now.month, 1)
                if now.month == 12:
                    end_date = date(now.year + 1, 1, 1)
                else:
                    end_date = date(now.year, now.month + 1, 1)

            result = await client.get_spending_plan(start_date=start_date, end_date=end_date)

            plan_text = f"📈 **Spending Plan for {start_date.strftime('%Y-%m')}**\n\n"
            plan_text += f"Plan data: {str(result)}\n"

            return [types.TextContent(type="text", text=plan_text)]

        elif name == "get_account_history":
            account_id = arguments.get("account_id")
            start_date = arguments.get("start_date")
            end_date = arguments.get("end_date")

            if not account_id:
                return [types.TextContent(
                    type="text",
                    text="Error: account_id is required for get_account_history"
                )]

            # Parse dates if provided
            parsed_start = None
            parsed_end = None
            if start_date:
                parsed_start = datetime.strptime(start_date, "%Y-%m-%d").date()
            if end_date:
                parsed_end = datetime.strptime(end_date, "%Y-%m-%d").date()

            result = await client.get_account_history(
                account_id=account_id,
                start_date=parsed_start,
                end_date=parsed_end
            )

            if not result:
                return [types.TextContent(
                    type="text",
                    text=f"No history found for account {account_id}"
                )]

            history_text = f"📊 **Account History for {account_id}**\n\n"
            history_text += f"History data: {str(result)}\n"

            return [types.TextContent(type="text", text=history_text)]

        else:
            return [types.TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]

    except Exception as e:
        error_msg = f"Error executing {name}: {str(e)}"
        logger.error(error_msg)
        return [types.TextContent(type="text", text=error_msg)]

async def main():
    """Main entry point for the MCP server"""
    # Run the server using stdio transport
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="monarchmoney-mcp",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())