"""
Working OAuth endpoints for MCP
Real implementation with actual tool discovery
"""

import json
import os
import secrets
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Monarch Money credentials for authentication
MONARCH_EMAIL = os.getenv("MONARCH_EMAIL")
MONARCH_PASSWORD = os.getenv("MONARCH_PASSWORD")
MONARCH_MFA_SECRET = os.getenv("MONARCH_MFA_SECRET")

# In-memory storage for OAuth clients (in production, use a database)
oauth_clients = {}
auth_codes = {}
access_tokens = {}

def generate_client_credentials():
    """Generate new OAuth client credentials"""
    client_id = f"monarchmoney_mcp_{secrets.token_hex(8)}"
    client_secret = secrets.token_urlsafe(32)
    return client_id, client_secret

def generate_auth_code(client_id):
    """Generate authorization code for client"""
    auth_code = secrets.token_urlsafe(32)
    auth_codes[auth_code] = client_id
    return auth_code

def generate_access_token(client_id):
    """Generate access token for client"""
    access_token = secrets.token_urlsafe(32)
    access_tokens[access_token] = client_id
    return access_token

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
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

        path = self.path

        # OAuth registration endpoint
        if "register" in path:
            # Generate new client credentials
            client_id, client_secret = generate_client_credentials()

            # Store client info
            oauth_clients[client_id] = {
                "client_secret": client_secret,
                "redirect_uris": [
                    "https://cesar-money-iy550m0ua-csar-e-benavides-projects.vercel.app/callback",
                    "http://localhost:3000/callback",
                    "mcp://oauth/callback"
                ],
                "created_at": json.dumps({"timestamp": "2024-09-26T18:21:12Z"})
            }

            response = {
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uris": oauth_clients[client_id]["redirect_uris"],
                "grant_types": ["authorization_code", "client_credentials"],
                "response_types": ["code", "token"],
                "scope": "mcp:read mcp:write accounts:read transactions:read budgets:read",
                "tools": AVAILABLE_TOOLS,
                "server_info": {
                    "name": "Monarch Money MCP Server",
                    "version": "1.0.0",
                    "description": "Access your Monarch Money financial data via MCP",
                    "protocol_version": "2024-11-05"
                }
            }
            self.wfile.write(json.dumps(response, indent=2).encode())
            return

        # OAuth authorization endpoint
        elif "authorize" in path:
            # Parse query parameters
            parsed_url = urlparse(path)
            query_params = parse_qs(parsed_url.query)

            # Extract OAuth parameters
            redirect_uri = query_params.get('redirect_uri', [''])[0]
            state = query_params.get('state', [''])[0]
            client_id = query_params.get('client_id', [''])[0]

            # Validate client_id exists
            if client_id not in oauth_clients:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                error_response = {"error": "invalid_client", "error_description": "Unknown client_id"}
                self.wfile.write(json.dumps(error_response).encode())
                return

            # Generate authorization code for this client
            auth_code = generate_auth_code(client_id)

            # Build callback URL with real parameters
            callback_url = f"{redirect_uri}?code={auth_code}&state={state}"

            self.send_response(302)
            self.send_header('Location', callback_url)
            self.end_headers()
            return

        # OAuth token endpoint
        elif "token" in path:
            # Handle POST data for token exchange
            if self.command == 'POST':
                content_length = int(self.headers.get('Content-Length', 0))
                post_data = self.rfile.read(content_length).decode('utf-8')
                token_params = parse_qs(post_data)
            else:
                # Fallback to query params for GET
                parsed_url = urlparse(path)
                token_params = parse_qs(parsed_url.query)

            auth_code = token_params.get('code', [''])[0]
            client_id = token_params.get('client_id', [''])[0]

            # Validate auth code and client
            if auth_code not in auth_codes or auth_codes[auth_code] != client_id:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                error_response = {"error": "invalid_grant", "error_description": "Invalid authorization code"}
                self.wfile.write(json.dumps(error_response).encode())
                return

            # Generate access token
            access_token = generate_access_token(client_id)

            # Remove used auth code
            del auth_codes[auth_code]

            response = {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": "mcp:read mcp:write accounts:read transactions:read budgets:read",
                "refresh_token": secrets.token_urlsafe(32),
                "server_url": "https://cesar-money-iy550m0ua-csar-e-benavides-projects.vercel.app"
            }
            self.wfile.write(json.dumps(response, indent=2).encode())
            return

        # Tool discovery endpoint
        elif "tools" in path or "capabilities" in path:
            response = {
                "tools": AVAILABLE_TOOLS,
                "capabilities": ["tools", "resources", "prompts"],
                "server_info": {
                    "name": "Monarch Money MCP Server",
                    "version": "1.0.0",
                    "description": "Access your Monarch Money financial data via MCP",
                    "protocol_version": "2024-11-05"
                }
            }
            self.wfile.write(json.dumps(response, indent=2).encode())
            return

        # Default response
        response = {
            "message": "Monarch Money MCP OAuth Server",
            "status": "active",
            "endpoints": [
                "/oauth/register",
                "/oauth/authorize",
                "/oauth/token",
                "/tools",
                "/capabilities"
            ],
            "tools_available": len(AVAILABLE_TOOLS),
            "server_info": {
                "name": "Monarch Money MCP Server",
                "version": "1.0.0",
                "description": "Access your Monarch Money financial data via MCP"
            }
        }
        self.wfile.write(json.dumps(response, indent=2).encode())

    def do_POST(self):
        self.do_GET()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()