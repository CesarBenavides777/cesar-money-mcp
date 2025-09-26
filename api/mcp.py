"""
MCP JSON-RPC Server for Agent.ai compatibility
Handles standard MCP protocol methods: tools/list, tools/call, etc.
"""

import os
import sys
import asyncio
import json
import logging
from http.server import BaseHTTPRequestHandler

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class handler(BaseHTTPRequestHandler):
    def check_authorization(self):
        """Check if request is authorized and return access token"""
        auth_header = self.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            access_token = auth_header.split(' ', 1)[1]

            # Import OAuth functions to validate token
            try:
                import sys
                import os
                sys.path.append(os.path.dirname(__file__))
                from oauth import validate_access_token, get_user_credentials

                # Validate the access token
                token_data = validate_access_token(access_token)
                if token_data:
                    # Return the access token for later use
                    return access_token
            except ImportError:
                pass

        # OAuth is required - no fallback to environment variables
        return None

    def send_unauthorized(self):
        """Send 401 Unauthorized with proper WWW-Authenticate header"""
        base_url = os.getenv("BASE_URL")
        if not base_url:
            host = self.headers.get('Host')
            if host:
                protocol = 'http' if 'localhost' in host or '127.0.0.1' in host else 'https'
                base_url = f"{protocol}://{host}"
            else:
                base_url = "https://cesar-money-mcp.vercel.app"

        self.send_response(401)
        self.send_header('Content-Type', 'application/json')
        self.send_header('WWW-Authenticate', f'Bearer realm="MCP Server", resource="{base_url}/.well-known/oauth-protected-resource"')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    async def execute_tool_with_credentials(self, tool_name, arguments, user_credentials):
        """Execute tool with user's OAuth credentials"""
        # Import required modules
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from monarchmoney import MonarchMoney, RequireMFAException

        # Create Monarch client with user's credentials
        client = MonarchMoney()
        try:
            await client.login(
                email=user_credentials["email"],
                password=user_credentials["password"],
                save_session=False,
                use_saved_session=False
            )
        except RequireMFAException:
            return "MFA required but not configured for OAuth flow"
        except Exception as e:
            return f"Authentication failed: {str(e)}"

        # Execute the requested tool
        try:
            if tool_name == "get_accounts":
                result = await client.get_accounts()
                accounts = result.get('accounts', [])
                if not accounts:
                    return "No accounts found."

                account_summary = f"Found {len(accounts)} accounts:\n\n"
                for account in accounts:
                    name_str = account.get('displayName') or 'Unknown Account'
                    balance = account.get('currentBalance') or 0

                    # Safely extract account type
                    type_obj = account.get('type') or {}
                    account_type = type_obj.get('display') or 'Unknown'

                    # Safely extract institution name
                    institution_obj = account.get('institution') or {}
                    institution = institution_obj.get('name') or 'Unknown'

                    account_summary += f"📊 **{name_str}**\n"
                    account_summary += f"   Balance: ${balance:,.2f}\n"
                    account_summary += f"   Type: {account_type}\n"
                    account_summary += f"   Institution: {institution}\n"
                    account_summary += f"   ID: {account.get('id') or 'N/A'}\n\n"

                return account_summary

            elif tool_name == "get_transactions":
                # Parse date arguments
                kwargs = {"limit": arguments.get("limit", 100)}
                start_date = arguments.get("start_date")
                end_date = arguments.get("end_date")

                if start_date:
                    from datetime import datetime
                    try:
                        parsed_start = datetime.strptime(start_date, "%Y-%m-%d").date()
                        kwargs["start_date"] = parsed_start.isoformat()
                    except ValueError:
                        return "Invalid start_date format. Use YYYY-MM-DD format."

                if end_date:
                    from datetime import datetime
                    try:
                        parsed_end = datetime.strptime(end_date, "%Y-%m-%d").date()
                        kwargs["end_date"] = parsed_end.isoformat()
                    except ValueError:
                        return "Invalid end_date format. Use YYYY-MM-DD format."

                if arguments.get("account_id"):
                    kwargs["account_id"] = arguments["account_id"]

                result = await client.get_transactions(**kwargs)
                transactions = result.get('allTransactions', {}).get('results', [])

                if not transactions:
                    return "No transactions found for the specified criteria."

                summary = f"Found {len(transactions)} transactions:\n\n"
                for tx in transactions[:20]:  # Show first 20
                    date_str = tx.get('date') or 'Unknown'

                    # Safely extract merchant name
                    merchant_obj = tx.get('merchant') or {}
                    merchant = merchant_obj.get('name') or 'Unknown Merchant'

                    amount = tx.get('amount') or 0

                    # Safely extract category name
                    category_obj = tx.get('category') or {}
                    category = category_obj.get('name') or 'Uncategorized'

                    summary += f"💳 **{date_str}** - {merchant}\n"
                    summary += f"   Amount: ${amount:,.2f}\n"
                    summary += f"   Category: {category}\n\n"

                if len(transactions) > 20:
                    summary += f"... and {len(transactions) - 20} more transactions\n"

                return summary

            # Add other tools as needed...
            else:
                return f"Tool '{tool_name}' not yet implemented for OAuth flow"

        except Exception as e:
            return f"Error executing {tool_name}: {str(e)}"

    def do_POST(self):
        """Handle JSON-RPC requests"""
        try:
            # Set CORS headers
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
            self.end_headers()

            # Read and parse request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')

            try:
                request_data = json.loads(body)
            except json.JSONDecodeError:
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {"code": -32700, "message": "Parse error"},
                    "id": None
                }
                self.wfile.write(json.dumps(error_response).encode())
                return

            # Extract JSON-RPC fields
            method = request_data.get("method")
            params = request_data.get("params", {})
            request_id = request_data.get("id")

            logger.info(f"MCP request: {method}")

            if not method:
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {"code": -32600, "message": "Invalid Request"},
                    "id": request_id
                }
                self.wfile.write(json.dumps(error_response).encode())
                return

            # Check if authentication is required for this method
            auth_required_methods = ["tools/call"]
            requires_auth = method in auth_required_methods

            if requires_auth:
                # Check authorization and get access token
                access_token = self.check_authorization()
                if not access_token:
                    self.send_unauthorized()
                    return
            else:
                access_token = None

            # Handle different MCP methods
            if method == "tools/list":
                response = {
                    "jsonrpc": "2.0",
                    "result": {
                        "tools": [
                            {
                                "name": "get_accounts",
                                "description": "Get all Monarch Money accounts with balances and details",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {},
                                    "required": []
                                }
                            },
                            {
                                "name": "get_transactions",
                                "description": "Get Monarch Money transactions with optional filtering",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format"},
                                        "end_date": {"type": "string", "description": "End date in YYYY-MM-DD format"},
                                        "limit": {"type": "integer", "description": "Maximum number of transactions (default: 100, max: 500)", "default": 100},
                                        "account_id": {"type": "string", "description": "Optional account ID to filter transactions"}
                                    },
                                    "required": []
                                }
                            },
                            {
                                "name": "get_budgets",
                                "description": "Get Monarch Money budget information and categories",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {},
                                    "required": []
                                }
                            },
                            {
                                "name": "get_spending_plan",
                                "description": "Get spending plan for a specific month",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "month": {"type": "string", "description": "Month in YYYY-MM format (defaults to current month)"}
                                    },
                                    "required": []
                                }
                            },
                            {
                                "name": "get_account_history",
                                "description": "Get balance history for a specific account",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "account_id": {"type": "string", "description": "Account ID to get history for"},
                                        "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format"},
                                        "end_date": {"type": "string", "description": "End date in YYYY-MM-DD format"}
                                    },
                                    "required": ["account_id"]
                                }
                            }
                        ]
                    },
                    "id": request_id
                }

            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})

                if not tool_name:
                    error_response = {
                        "jsonrpc": "2.0",
                        "error": {"code": -32602, "message": "Invalid params - missing tool name"},
                        "id": request_id
                    }
                    self.wfile.write(json.dumps(error_response).encode())
                    return

                # Execute tool asynchronously with user credentials if available
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                try:
                    # Get user credentials from access token if available
                    user_credentials = None
                    if access_token and access_token != "env_fallback":
                        try:
                            from oauth import get_user_credentials
                            user_credentials = get_user_credentials(access_token)
                        except ImportError:
                            pass

                    # Execute tool with appropriate credentials
                    if user_credentials:
                        # Use user's OAuth credentials
                        result = loop.run_until_complete(
                            self.execute_tool_with_credentials(
                                tool_name, arguments, user_credentials
                            )
                        )
                    else:
                        # Fall back to environment variables (existing behavior)
                        from fastmcp_server import mcp as fastmcp_server
                        tools = loop.run_until_complete(fastmcp_server.get_tools())

                        if tool_name not in tools:
                            raise ValueError(f"Unknown tool: {tool_name}")

                        tool = tools[tool_name]
                        tool_result = loop.run_until_complete(tool.run(arguments))

                        # Extract the text content from the result
                        result = ""
                        if tool_result.content:
                            for content in tool_result.content:
                                if hasattr(content, 'text'):
                                    result += content.text

                    response = {
                        "jsonrpc": "2.0",
                        "result": {
                            "content": [{"type": "text", "text": str(result)}]
                        },
                        "id": request_id
                    }
                except Exception as e:
                    logger.error(f"Tool execution error: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
                        "id": request_id
                    }
                    self.wfile.write(json.dumps(error_response).encode())
                    return
                finally:
                    loop.close()

            elif method == "initialize":
                response = {
                    "jsonrpc": "2.0",
                    "result": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {
                            "tools": {
                                "listChanged": False
                            }
                        },
                        "serverInfo": {
                            "name": "Monarch Money MCP Server",
                            "version": "1.0.0",
                            "description": "Access your Monarch Money financial data via MCP"
                        }
                    },
                    "id": request_id
                }

            elif method == "initialized":
                response = {
                    "jsonrpc": "2.0",
                    "result": {},
                    "id": request_id
                }

            else:
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                    "id": request_id
                }
                self.wfile.write(json.dumps(error_response).encode())
                return

            # Send successful response
            self.wfile.write(json.dumps(response).encode())

        except Exception as e:
            logger.error(f"MCP handler error: {e}")
            error_response = {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": "Internal error"},
                "id": None
            }
            self.wfile.write(json.dumps(error_response).encode())

    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()