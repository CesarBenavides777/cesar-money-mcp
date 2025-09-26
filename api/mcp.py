"""
MCP Protocol Server for Monarch Money
Implements the Model Context Protocol specification
"""

import json
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

# Import monarchmoney library
from monarchmoney import MonarchMoney, RequireMFAException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
API_KEY = os.getenv("API_KEY")
MONARCH_EMAIL = os.getenv("MONARCH_EMAIL")
MONARCH_PASSWORD = os.getenv("MONARCH_PASSWORD")
MONARCH_MFA_SECRET = os.getenv("MONARCH_MFA_SECRET")

class MCPServer:
    """MCP Protocol Server Implementation"""

    def __init__(self):
        self.name = "monarchmoney-mcp"
        self.version = "1.0.0"

    async def get_monarch_client(self) -> MonarchMoney:
        """Create and authenticate Monarch Money client"""
        if not MONARCH_EMAIL or not MONARCH_PASSWORD:
            raise ValueError("Monarch credentials not configured")

        client = MonarchMoney()
        try:
            await client.login(
                email=MONARCH_EMAIL,
                password=MONARCH_PASSWORD,
                mfa_secret_key=MONARCH_MFA_SECRET,
                save_session=False,
                use_saved_session=False
            )
            return client
        except RequireMFAException:
            raise Exception("MFA required but not configured")
        except Exception as e:
            logger.error(f"Monarch login failed: {e}")
            raise Exception(f"Authentication failed: {str(e)}")

    def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP initialize request"""
        return {
            "protocolVersion": params.get("protocolVersion", "2024-11-05"),
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": self.name,
                "version": self.version
            }
        }

    def handle_list_tools(self) -> Dict[str, Any]:
        """Handle tools/list request"""
        return {
            "tools": [
                {
                    "name": "get_accounts",
                    "description": "Get all Monarch Money accounts",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                },
                {
                    "name": "get_transactions",
                    "description": "Get Monarch Money transactions",
                    "inputSchema": {
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
                                "description": "Maximum number of transactions",
                                "default": 100
                            }
                        },
                        "required": []
                    }
                },
                {
                    "name": "get_budgets",
                    "description": "Get Monarch Money budgets",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                },
                {
                    "name": "get_spending_plan",
                    "description": "Get current month's spending plan",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            ]
        }

    async def handle_call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request"""
        try:
            client = await self.get_monarch_client()

            if name == "get_accounts":
                result = await client.get_accounts()
                accounts = result.get('accounts', [])
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Found {len(accounts)} accounts:\n" +
                                   "\n".join([f"- {acc.get('displayName', 'Unknown')}: ${acc.get('currentBalance', 0):.2f}"
                                            for acc in accounts])
                        }
                    ]
                }

            elif name == "get_transactions":
                start_date = arguments.get("start_date")
                end_date = arguments.get("end_date")
                limit = min(int(arguments.get("limit", 100)), 1000)

                # Parse dates if provided
                if start_date:
                    start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                if end_date:
                    end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

                result = await client.get_transactions(
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit
                )

                transactions = result.get('allTransactions', {}).get('results', [])

                summary = f"Found {len(transactions)} transactions"
                if start_date:
                    summary += f" from {start_date}"
                if end_date:
                    summary += f" to {end_date}"

                transaction_text = "\n".join([
                    f"- {tx.get('date', 'Unknown')}: {tx.get('merchant', {}).get('name', 'Unknown')} ${tx.get('amount', 0):.2f}"
                    for tx in transactions[:10]  # Show first 10
                ])

                if len(transactions) > 10:
                    transaction_text += f"\n... and {len(transactions) - 10} more"

                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"{summary}:\n{transaction_text}"
                        }
                    ]
                }

            elif name == "get_budgets":
                result = await client.get_budgets()
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Budget data retrieved:\n{json.dumps(result, indent=2)}"
                        }
                    ]
                }

            elif name == "get_spending_plan":
                now = datetime.now()
                result = await client.get_spending_plan(
                    start_date=datetime(now.year, now.month, 1).date(),
                    end_date=datetime(now.year, now.month + 1 if now.month < 12 else 1, 1).date()
                )
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Spending plan for {now.year}-{now.month:02d}:\n{json.dumps(result, indent=2)}"
                        }
                    ]
                }

            else:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Unknown tool: {name}"
                        }
                    ],
                    "isError": True
                }

        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error executing {name}: {str(e)}"
                    }
                ],
                "isError": True
            }

def verify_auth(headers: Dict[str, str]) -> bool:
    """Verify API key authentication"""
    if not API_KEY:
        return False

    provided_key = headers.get("x-api-key") or headers.get("X-API-Key")
    if not provided_key:
        return False

    import hmac
    return hmac.compare_digest(provided_key, API_KEY)

async def handle_mcp_request(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle MCP protocol requests"""
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, X-API-Key"
    }

    # Handle preflight
    if event.get("httpMethod") == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": headers,
            "body": ""
        }

    # Verify authentication
    request_headers = event.get("headers", {})
    if not verify_auth(request_headers):
        return {
            "statusCode": 401,
            "headers": headers,
            "body": json.dumps({
                "error": {
                    "code": -32600,
                    "message": "Invalid authentication"
                }
            })
        }

    # Parse JSON-RPC request
    try:
        body = event.get("body", "{}")
        if isinstance(body, str):
            request_data = json.loads(body)
        else:
            request_data = body
    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "headers": headers,
            "body": json.dumps({
                "error": {
                    "code": -32700,
                    "message": "Parse error"
                }
            })
        }

    # Initialize MCP server
    mcp_server = MCPServer()

    # Handle different MCP methods
    method = request_data.get("method")
    params = request_data.get("params", {})
    request_id = request_data.get("id")

    try:
        if method == "initialize":
            result = mcp_server.handle_initialize(params)
        elif method == "tools/list":
            result = mcp_server.handle_list_tools()
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            result = await mcp_server.handle_call_tool(tool_name, tool_args)
        else:
            return {
                "statusCode": 400,
                "headers": headers,
                "body": json.dumps({
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    },
                    "id": request_id
                })
            }

        # Return successful response
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            })
        }

    except Exception as e:
        logger.error(f"MCP request error: {e}")
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps({
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                },
                "id": request_id
            })
        }

def handler(event, context):
    """Vercel handler for MCP requests"""
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        return loop.run_until_complete(handle_mcp_request(event))
    finally:
        loop.close()