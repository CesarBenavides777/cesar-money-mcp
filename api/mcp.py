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
        """Check if request is authorized - optional for this implementation"""
        # For now, we'll allow unauthenticated access for testing
        # In production, you'd validate Bearer tokens here
        auth_header = self.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            # Token validation would go here
            return True
        # Allow unauthenticated access for demo purposes
        return True

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

    def do_POST(self):
        """Handle JSON-RPC requests"""
        try:
            # Check authorization first (currently allows all for demo)
            if not self.check_authorization():
                self.send_unauthorized()
                return

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

                # Execute tool asynchronously
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                try:
                    # For now, always use the environment variable server
                    # OAuth integration would require updating the tool signatures
                    from fastmcp_server import mcp as fastmcp_server

                    # Get tools from FastMCP (async method)
                    tools = loop.run_until_complete(fastmcp_server.get_tools())

                    # Check if tool exists
                    if tool_name not in tools:
                        raise ValueError(f"Unknown tool: {tool_name}")

                    # Get the tool and execute it using run method
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