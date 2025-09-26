"""
MCP Server Discovery Endpoint
Provides server capabilities and OAuth endpoints for MCP client discovery
"""

import json
import os
import logging
from http.server import BaseHTTPRequestHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Available MCP tools
AVAILABLE_TOOLS = [
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

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle MCP server discovery requests"""
        try:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
            self.end_headers()

            # Get base URL from environment or auto-detect from request
            base_url = os.getenv("BASE_URL")
            if not base_url:
                # Auto-detect from request headers (secure fallback)
                host = self.headers.get('Host')
                if host:
                    # Use HTTPS in production, HTTP only for localhost
                    protocol = 'http' if 'localhost' in host or '127.0.0.1' in host else 'https'
                    base_url = f"{protocol}://{host}"
                else:
                    # Final fallback
                    base_url = "https://your-mcp-server.vercel.app"

            discovery_response = {
                "name": "Monarch Money MCP Server",
                "version": "1.0.0",
                "description": "Access your Monarch Money financial data via MCP",
                "protocol_version": "2025-06-18",
                "server_info": {
                    "name": "Monarch Money MCP Server",
                    "version": "1.0.0",
                    "description": "Access your Monarch Money financial data via MCP",
                    "protocol_version": "2025-06-18"
                },
                "capabilities": {
                    "tools": {
                        "list_changed": False
                    },
                    "resources": {},
                    "prompts": {}
                },
                "oauth": {
                    "authorization_endpoint": f"{base_url}/oauth/authorize",
                    "token_endpoint": f"{base_url}/oauth/token",
                    "registration_endpoint": f"{base_url}/oauth/register",
                    "grant_types_supported": ["authorization_code"],
                    "response_types_supported": ["code"],
                    "scopes_supported": ["mcp:read", "mcp:write"],
                    "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post"]
                },
                "endpoints": {
                    "mcp": f"{base_url}/mcp",
                    "tools": f"{base_url}/tools/call",
                    "oauth_register": f"{base_url}/oauth/register",
                    "oauth_authorize": f"{base_url}/oauth/authorize",
                    "oauth_token": f"{base_url}/oauth/token"
                },
                "tools": AVAILABLE_TOOLS
            }

            self.wfile.write(json.dumps(discovery_response, indent=2).encode())

        except Exception as e:
            logger.error(f"Discovery endpoint error: {e}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error_response = {
                "error": "server_error",
                "error_description": f"Discovery failed: {str(e)}"
            }
            self.wfile.write(json.dumps(error_response).encode())

    def do_POST(self):
        self.do_GET()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()