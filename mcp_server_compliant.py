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

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("monarchmoney-mcp")

try:
    from mcp.server import Server
    from mcp.types import (
        Tool,
        TextContent,
        CallToolRequest,
        CallToolResult,
        ListToolsRequest,
        ListToolsResult,
        ErrorCode,
        McpError,
        InitializeRequest,
        InitializeResult,
        ServerCapabilities,
        ToolCapabilities
    )
    from mcp.server.stdio import stdio_server
    from mcp.server.sse import sse_server

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

# MCP Server Implementation
class MonarchMCPServer:
    """MCP-compliant Monarch Money server implementation"""

    def __init__(self):
        self.server = Server(config.server_name)
        self._setup_handlers()

    def _setup_handlers(self):
        """Setup all MCP protocol handlers"""

        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """List all available tools following MCP 2025-06-18 specification"""
            try:
                return [
                    Tool(
                        name="get_accounts",
                        description="Get all Monarch Money accounts with balances and details. Returns comprehensive account information including current balances, account types, and institution details.",
                        inputSchema={
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    ),
                    Tool(
                        name="get_transactions",
                        description="Get Monarch Money transactions with optional filtering. Supports date range filtering, account-specific queries, and pagination.",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "start_date": {
                                    "type": "string",
                                    "description": "Start date in YYYY-MM-DD format",
                                    "pattern": r"^\d{4}-\d{2}-\d{2}$"
                                },
                                "end_date": {
                                    "type": "string",
                                    "description": "End date in YYYY-MM-DD format",
                                    "pattern": r"^\d{4}-\d{2}-\d{2}$"
                                },
                                "limit": {
                                    "type": "integer",
                                    "description": "Maximum number of transactions (1-1000)",
                                    "minimum": 1,
                                    "maximum": 1000,
                                    "default": 100
                                },
                                "account_id": {
                                    "type": "string",
                                    "description": "Optional account ID to filter transactions"
                                }
                            },
                            "required": []
                        }
                    ),
                    Tool(
                        name="get_budgets",
                        description="Get Monarch Money budget information and categories. Returns budget data and spending categories.",
                        inputSchema={
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    ),
                    Tool(
                        name="get_spending_plan",
                        description="Get spending plan for a specific month. Returns detailed spending plan information and budget allocations.",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "month": {
                                    "type": "string",
                                    "description": "Month in YYYY-MM format (defaults to current month)",
                                    "pattern": r"^\d{4}-\d{2}$"
                                }
                            },
                            "required": []
                        }
                    ),
                    Tool(
                        name="get_account_history",
                        description="Get balance history for a specific account. Returns historical balance data over time.",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "account_id": {
                                    "type": "string",
                                    "description": "Account ID to get history for"
                                },
                                "start_date": {
                                    "type": "string",
                                    "description": "Start date in YYYY-MM-DD format",
                                    "pattern": r"^\d{4}-\d{2}-\d{2}$"
                                },
                                "end_date": {
                                    "type": "string",
                                    "description": "End date in YYYY-MM-DD format",
                                    "pattern": r"^\d{4}-\d{2}-\d{2}$"
                                }
                            },
                            "required": ["account_id"]
                        }
                    )
                ]
            except Exception as e:
                logger.error(f"Error in list_tools: {e}")
                raise McpError(ErrorCode.INTERNAL_ERROR, f"Failed to list tools: {str(e)}")

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Call a tool following MCP 2025-06-18 specification"""
            try:
                logger.info(f"Calling tool: {name} with arguments: {arguments}")

                # Get authenticated client
                client = await self._get_monarch_client()

                # Route to appropriate handler
                if name == "get_accounts":
                    result = await self._handle_get_accounts(client)
                elif name == "get_transactions":
                    request = GetTransactionsRequest(**arguments)
                    result = await self._handle_get_transactions(client, request)
                elif name == "get_budgets":
                    result = await self._handle_get_budgets(client)
                elif name == "get_spending_plan":
                    request = GetSpendingPlanRequest(**arguments)
                    result = await self._handle_get_spending_plan(client, request)
                elif name == "get_account_history":
                    request = GetAccountHistoryRequest(**arguments)
                    result = await self._handle_get_account_history(client, request)
                else:
                    raise McpError(ErrorCode.METHOD_NOT_FOUND, f"Unknown tool: {name}")

                return [TextContent(type="text", text=result)]

            except McpError:
                raise
            except Exception as e:
                logger.error(f"Error in call_tool {name}: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise McpError(ErrorCode.INTERNAL_ERROR, f"Tool execution failed: {str(e)}")

    async def _get_monarch_client(self) -> MonarchMoney:
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
            raise McpError(ErrorCode.INVALID_PARAMS, "MFA is required but MONARCH_MFA_SECRET is not configured")
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise McpError(ErrorCode.INTERNAL_ERROR, f"Failed to authenticate with Monarch Money: {str(e)}")

    async def _handle_get_accounts(self, client: MonarchMoney) -> str:
        """Handle get_accounts tool call with proper string safety"""
        try:
            result = await client.get_accounts()
            accounts = result.get('accounts', [])

            if not accounts:
                return "No accounts found."

            account_summary = f"Found {len(accounts)} accounts:\n\n"

            for account in accounts:
                # Safe string extraction with explicit str() conversion
                name_str = str(account.get('displayName') or 'Unknown Account')
                balance = account.get('currentBalance') or 0

                # Safely extract account type
                type_obj = account.get('type') or {}
                account_type = str(type_obj.get('display') or 'Unknown')

                # Safely extract institution name
                institution_obj = account.get('institution') or {}
                institution = str(institution_obj.get('name') or 'Unknown')

                account_id = str(account.get('id') or 'N/A')

                account_summary += f"📊 **{name_str}**\n"
                account_summary += f"   Balance: ${balance:,.2f}\n"
                account_summary += f"   Type: {account_type}\n"
                account_summary += f"   Institution: {institution}\n"
                account_summary += f"   ID: {account_id}\n\n"

            return account_summary

        except Exception as e:
            logger.error(f"Error in _handle_get_accounts: {e}")
            raise McpError(ErrorCode.INTERNAL_ERROR, f"Failed to fetch accounts: {str(e)}")

    async def _handle_get_transactions(self, client: MonarchMoney, request: GetTransactionsRequest) -> str:
        """Handle get_transactions tool call with proper validation"""
        try:
            # Build query parameters
            kwargs = {"limit": request.limit}

            if request.start_date:
                parsed_start = datetime.strptime(request.start_date, "%Y-%m-%d").date()
                kwargs["start_date"] = parsed_start.isoformat()

            if request.end_date:
                parsed_end = datetime.strptime(request.end_date, "%Y-%m-%d").date()
                kwargs["end_date"] = parsed_end.isoformat()

            if request.account_id:
                kwargs["account_id"] = request.account_id

            result = await client.get_transactions(**kwargs)
            transactions = result.get('allTransactions', {}).get('results', [])

            if not transactions:
                return "No transactions found for the specified criteria."

            summary = f"Found {len(transactions)} transactions"
            if request.start_date:
                summary += f" from {request.start_date}"
            if request.end_date:
                summary += f" to {request.end_date}"
            summary += f" (showing up to {request.limit}):\n\n"

            # Show first 20 transactions for readability
            for tx in transactions[:20]:
                # Safe string extraction
                date_str = str(tx.get('date') or 'Unknown')

                merchant_obj = tx.get('merchant') or {}
                merchant = str(merchant_obj.get('name') or 'Unknown Merchant')

                amount = tx.get('amount') or 0

                category_obj = tx.get('category') or {}
                category = str(category_obj.get('name') or 'Uncategorized')

                account_obj = tx.get('account') or {}
                account_name = str(account_obj.get('displayName') or 'Unknown Account')

                summary += f"💳 **{date_str}** - {merchant}\n"
                summary += f"   Amount: ${amount:,.2f}\n"
                summary += f"   Category: {category}\n"
                summary += f"   Account: {account_name}\n\n"

            if len(transactions) > 20:
                summary += f"... and {len(transactions) - 20} more transactions\n"

            return summary

        except ValueError as e:
            raise McpError(ErrorCode.INVALID_PARAMS, f"Invalid date format: {str(e)}")
        except Exception as e:
            logger.error(f"Error in _handle_get_transactions: {e}")
            raise McpError(ErrorCode.INTERNAL_ERROR, f"Failed to fetch transactions: {str(e)}")

    async def _handle_get_budgets(self, client: MonarchMoney) -> str:
        """Handle get_budgets tool call"""
        try:
            result = await client.get_budgets()

            if not result:
                return "No budget information available."

            budget_text = "📊 **Budget Information**\n\n"

            if isinstance(result, list):
                for budget in result:
                    # Safe string extraction
                    name = str(budget.get('name') or 'Unnamed Budget')
                    budget_text += f"Budget: {name}\n"
            else:
                budget_text += f"Budget data: {str(result)}\n"

            return budget_text

        except Exception as e:
            logger.error(f"Error in _handle_get_budgets: {e}")
            raise McpError(ErrorCode.INTERNAL_ERROR, f"Failed to fetch budgets: {str(e)}")

    async def _handle_get_spending_plan(self, client: MonarchMoney, request: GetSpendingPlanRequest) -> str:
        """Handle get_spending_plan tool call"""
        try:
            if request.month:
                # Parse YYYY-MM format
                year, month_num = map(int, request.month.split('-'))
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

            result = await client.get_spending_plan(
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat()
            )

            plan_text = f"📈 **Spending Plan for {start_date.strftime('%Y-%m')}**\n\n"
            plan_text += f"Plan data: {str(result)}\n"

            return plan_text

        except ValueError as e:
            raise McpError(ErrorCode.INVALID_PARAMS, f"Invalid month format: {str(e)}")
        except Exception as e:
            logger.error(f"Error in _handle_get_spending_plan: {e}")
            raise McpError(ErrorCode.INTERNAL_ERROR, f"Failed to fetch spending plan: {str(e)}")

    async def _handle_get_account_history(self, client: MonarchMoney, request: GetAccountHistoryRequest) -> str:
        """Handle get_account_history tool call"""
        try:
            # Parse dates if provided
            parsed_start = None
            parsed_end = None

            if request.start_date:
                parsed_start = datetime.strptime(request.start_date, "%Y-%m-%d").date()
            if request.end_date:
                parsed_end = datetime.strptime(request.end_date, "%Y-%m-%d").date()

            result = await client.get_account_history(
                account_id=request.account_id,
                start_date=parsed_start.isoformat() if parsed_start else None,
                end_date=parsed_end.isoformat() if parsed_end else None
            )

            if not result:
                return f"No history found for account {request.account_id}"

            history_text = f"📊 **Account History for {request.account_id}**\n\n"
            history_text += f"History data: {str(result)}\n"

            return history_text

        except ValueError as e:
            raise McpError(ErrorCode.INVALID_PARAMS, f"Invalid date format: {str(e)}")
        except Exception as e:
            logger.error(f"Error in _handle_get_account_history: {e}")
            raise McpError(ErrorCode.INTERNAL_ERROR, f"Failed to fetch account history: {str(e)}")

    def get_server(self) -> Server:
        """Get the MCP server instance"""
        return self.server

async def main():
    """Main entry point for the MCP server"""
    try:
        # Initialize server
        server_instance = MonarchMCPServer()
        server = server_instance.get_server()

        # Determine transport method
        # Support both stdio (for local) and SSE (for remote)
        transport = os.getenv("MCP_TRANSPORT", "stdio").lower()

        if transport == "sse":
            # SSE transport for remote MCP servers
            host = os.getenv("MCP_HOST", "0.0.0.0")
            port = int(os.getenv("MCP_PORT", "8000"))

            logger.info(f"Starting MCP server with SSE transport on {host}:{port}")
            logger.info(f"Protocol version: {config.protocol_version}")

            async with sse_server(server, host, port) as sse_context:
                await sse_context.run()
        else:
            # Default stdio transport for local MCP servers
            logger.info("Starting MCP server with stdio transport")
            logger.info(f"Protocol version: {config.protocol_version}")

            async with stdio_server(server) as stdio_context:
                await stdio_context.run()

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    # Run the server
    asyncio.run(main())