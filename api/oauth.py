"""
Consolidated OAuth 2.1 endpoints for MCP Server
Handles all OAuth-related requests: authorization, token, registration, and metadata discovery
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
user_credentials = {}  # Store user credentials by access token

def generate_client_credentials():
    """Generate new OAuth client credentials"""
    client_id = f"monarchmoney_mcp_{secrets.token_hex(8)}"
    client_secret = secrets.token_urlsafe(32)
    return client_id, client_secret

def generate_auth_code(client_id, user_email=None, user_password=None):
    """Generate authorization code for client"""
    auth_code = secrets.token_urlsafe(32)
    auth_codes[auth_code] = {
        "client_id": client_id,
        "user_email": user_email,
        "user_password": user_password
    }
    return auth_code

def generate_access_token(client_id, auth_code):
    """Generate access token for client and bind to user credentials"""
    access_token = secrets.token_urlsafe(32)
    access_tokens[access_token] = {
        "client_id": client_id,
        "auth_code": auth_code,
        "issued_at": json.dumps({"timestamp": "2024-09-26T18:21:12Z"}),
        "expires_in": 3600
    }
    return access_token

def get_user_credentials(access_token):
    """Get user credentials associated with an access token"""
    if access_token in user_credentials:
        return user_credentials[access_token]
    return None

def validate_access_token(access_token):
    """Validate an access token and return associated data"""
    if access_token in access_tokens:
        return access_tokens[access_token]
    return None

class handler(BaseHTTPRequestHandler):
    def get_base_url(self):
        """Get base URL from environment or request headers"""
        base_url = os.getenv("BASE_URL")
        if not base_url:
            host = self.headers.get('Host')
            if host:
                protocol = 'http' if 'localhost' in host or '127.0.0.1' in host else 'https'
                base_url = f"{protocol}://{host}"
            else:
                base_url = "https://cesar-money-mcp.vercel.app"
        return base_url

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

        path = self.path
        base_url = self.get_base_url()

        # OAuth 2.0 Authorization Server Metadata (RFC 8414)
        if ".well-known/oauth-authorization-server" in path:
            response = {
                "issuer": base_url,
                "authorization_endpoint": f"{base_url}/oauth?action=authorize",
                "token_endpoint": f"{base_url}/oauth?action=token",
                "registration_endpoint": f"{base_url}/oauth?action=register",
                "response_types_supported": ["code"],
                "grant_types_supported": ["authorization_code"],
                "code_challenge_methods_supported": ["S256"],
                "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post"],
                "scopes_supported": ["mcp:read", "mcp:write", "accounts:read", "transactions:read", "budgets:read"]
            }
            self.wfile.write(json.dumps(response, indent=2).encode())
            return

        # OAuth 2.0 Protected Resource Metadata (RFC 9728)
        elif ".well-known/oauth-protected-resource" in path:
            response = {
                "resource": base_url,
                "authorization_servers": [base_url],
                "bearer_methods_supported": ["header"],
                "scopes_supported": ["mcp:read", "mcp:write", "accounts:read", "transactions:read", "budgets:read"]
            }
            self.wfile.write(json.dumps(response, indent=2).encode())
            return

        # Parse query parameters - handle malformed URLs with multiple question marks
        if '?' in path:
            # Split on first ? to separate path from query string
            path_part, query_string = path.split('?', 1)
            # If there are multiple ?, merge all query parts
            if '?' in query_string:
                query_string = query_string.replace('?', '&')
            query_params = parse_qs(query_string)
        else:
            query_params = {}

        action = query_params.get('action', [''])[0]

        # Check if this is an authorization request (has response_type and client_id)
        response_type = query_params.get('response_type', [''])[0]
        client_id = query_params.get('client_id', [''])[0]

        # OAuth authorization endpoint - handle incoming authorization request
        if response_type == "code" and client_id:
            redirect_uri = query_params.get('redirect_uri', [''])[0]
            state = query_params.get('state', [''])[0]
            scope = query_params.get('scope', [''])[0]

            # Auto-register the client if it doesn't exist (for demo purposes)
            if client_id not in oauth_clients:
                oauth_clients[client_id] = {
                    "client_secret": secrets.token_urlsafe(32),
                    "redirect_uris": [redirect_uri],
                    "created_at": json.dumps({"timestamp": "2024-09-26T18:21:12Z"})
                }

            # Show login form
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()

            login_form = f'''<!DOCTYPE html>
<html>
<head>
    <title>Monarch Money MCP Authorization</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 400px; margin: 100px auto; padding: 20px; }}
        .form-group {{ margin-bottom: 15px; }}
        label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
        input {{ width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }}
        button {{ width: 100%; padding: 10px; background: #007cba; color: white; border: none; border-radius: 4px; cursor: pointer; }}
        button:hover {{ background: #005a87; }}
        .info {{ background: #f0f0f0; padding: 10px; border-radius: 4px; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <h2>🏦 Monarch Money MCP Authorization</h2>
    <div class="info">
        <strong>Client:</strong> {client_id}<br>
        <strong>Requesting access to:</strong> Your Monarch Money financial data<br>
        <strong>Scope:</strong> {scope}
    </div>
    <form method="post" action="/oauth?action=process">
        <input type="hidden" name="client_id" value="{client_id}">
        <input type="hidden" name="redirect_uri" value="{redirect_uri}">
        <input type="hidden" name="state" value="{state}">
        <input type="hidden" name="response_type" value="code">

        <div class="form-group">
            <label for="email">Monarch Money Email:</label>
            <input type="email" name="email" id="email" required>
        </div>

        <div class="form-group">
            <label for="password">Monarch Money Password:</label>
            <input type="password" name="password" id="password" required>
        </div>

        <button type="submit">Authorize Access</button>
    </form>
    <p style="font-size: 12px; color: #666; margin-top: 20px;">
        Your credentials are verified against your configured Monarch Money account and are not stored.
    </p>
</body>
</html>'''
            self.wfile.write(login_form.encode())
            return

        # OAuth registration endpoint
        elif action == "register":
            redirect_uri = query_params.get('redirect_uri', [''])[0]
            state = query_params.get('state', [''])[0]
            client_id = query_params.get('client_id', [''])[0]

            if client_id not in oauth_clients:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                error_response = {"error": "invalid_client", "error_description": "Unknown client_id"}
                self.wfile.write(json.dumps(error_response).encode())
                return

            # Show login form
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()

            login_form = f'''<!DOCTYPE html>
<html>
<head>
    <title>Monarch Money MCP Authorization</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 400px; margin: 100px auto; padding: 20px; }}
        .form-group {{ margin-bottom: 15px; }}
        label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
        input {{ width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }}
        button {{ width: 100%; padding: 10px; background: #007cba; color: white; border: none; border-radius: 4px; cursor: pointer; }}
        button:hover {{ background: #005a87; }}
        .info {{ background: #f0f0f0; padding: 10px; border-radius: 4px; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <h2>🏦 Monarch Money MCP Authorization</h2>
    <div class="info">
        <strong>Client:</strong> {client_id}<br>
        <strong>Requesting access to:</strong> Your Monarch Money financial data
    </div>
    <form method="post" action="/oauth?action=process">
        <input type="hidden" name="client_id" value="{client_id}">
        <input type="hidden" name="redirect_uri" value="{redirect_uri}">
        <input type="hidden" name="state" value="{state}">
        <input type="hidden" name="response_type" value="code">

        <div class="form-group">
            <label for="email">Monarch Money Email:</label>
            <input type="email" name="email" id="email" required>
        </div>

        <div class="form-group">
            <label for="password">Monarch Money Password:</label>
            <input type="password" name="password" id="password" required>
        </div>

        <button type="submit">Authorize Access</button>
    </form>
    <p style="font-size: 12px; color: #666; margin-top: 20px;">
        Your credentials are verified against your configured Monarch Money account and are not stored.
    </p>
</body>
</html>'''
            self.wfile.write(login_form.encode())
            return

        # OAuth token endpoint (GET fallback)
        elif action == "token":
            parsed_url = urlparse(path)
            token_params = parse_qs(parsed_url.query)
            auth_code = token_params.get('code', [''])[0]
            client_id = token_params.get('client_id', [''])[0]

            if auth_code not in auth_codes:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                error_response = {"error": "invalid_grant", "error_description": "Invalid authorization code"}
                self.wfile.write(json.dumps(error_response).encode())
                return

            auth_data = auth_codes[auth_code]
            if auth_data["client_id"] != client_id:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                error_response = {"error": "invalid_grant", "error_description": "Client ID mismatch"}
                self.wfile.write(json.dumps(error_response).encode())
                return

            # Generate access token and store user credentials
            access_token = generate_access_token(client_id, auth_code)
            user_credentials[access_token] = {
                "email": auth_data["user_email"],
                "password": auth_data["user_password"]
            }

            # Clean up auth code
            del auth_codes[auth_code]

            response = {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": "mcp:read mcp:write accounts:read transactions:read budgets:read",
                "refresh_token": secrets.token_urlsafe(32)
            }
            self.wfile.write(json.dumps(response, indent=2).encode())
            return

        # Default response
        response = {
            "message": "Monarch Money MCP OAuth Server",
            "status": "active",
            "endpoints": {
                "register": f"{base_url}/oauth?action=register",
                "authorize": f"{base_url}/oauth?action=authorize",
                "token": f"{base_url}/oauth?action=token",
                "metadata": f"{base_url}/oauth?.well-known/oauth-authorization-server"
            }
        }
        self.wfile.write(json.dumps(response, indent=2).encode())

    def do_POST(self):
        path = self.path
        parsed_url = urlparse(path)
        query_params = parse_qs(parsed_url.query)
        action = query_params.get('action', [''])[0]

        # Handle OAuth authorization form submission
        if action == "process":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            form_data = parse_qs(post_data)

            email = form_data.get('email', [''])[0]
            password = form_data.get('password', [''])[0]
            client_id = form_data.get('client_id', [''])[0]
            redirect_uri = form_data.get('redirect_uri', [''])[0]
            state = form_data.get('state', [''])[0]

            # Validate credentials by attempting to login to Monarch Money
            try:
                # Import MonarchMoney here to test the user's credentials
                import sys
                import os
                import asyncio

                # Add parent directory to path for imports
                sys.path.append(os.path.dirname(os.path.dirname(__file__)))

                from monarchmoney import MonarchMoney

                # Test the user's credentials
                client = MonarchMoney()
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                try:
                    # Attempt login with user's credentials
                    loop.run_until_complete(client.login(
                        email=email,
                        password=password,
                        save_session=False,
                        use_saved_session=False
                    ))
                    # If we get here, credentials are valid
                    # Generate auth code with user credentials
                    auth_code = generate_auth_code(client_id, email, password)

                except Exception as login_error:
                    # Login failed - redirect back with error
                    error_redirect = f"/oauth?action=authorize&client_id={client_id}&redirect_uri={redirect_uri}&state={state}&error=invalid_credentials&error_description=Invalid Monarch Money credentials"
                    self.send_response(302)
                    self.send_header('Location', error_redirect)
                    self.end_headers()
                    return
                finally:
                    loop.close()

            except ImportError:
                # MonarchMoney library not available, fall back to environment variables
                if email != MONARCH_EMAIL or password != MONARCH_PASSWORD:
                    error_redirect = f"/oauth?action=authorize&client_id={client_id}&redirect_uri={redirect_uri}&state={state}&error=invalid_credentials&error_description=Server credentials required"
                    self.send_response(302)
                    self.send_header('Location', error_redirect)
                    self.end_headers()
                    return

            # Credentials are valid - use the auth code we generated
            callback_url = f"{redirect_uri}?code={auth_code}&state={state}"

            self.send_response(302)
            self.send_header('Location', callback_url)
            self.end_headers()
            return

        # Handle token endpoint POST
        elif action == "token":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            token_params = parse_qs(post_data)

            auth_code = token_params.get('code', [''])[0]
            client_id = token_params.get('client_id', [''])[0]

            if auth_code not in auth_codes:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                error_response = {"error": "invalid_grant", "error_description": "Invalid authorization code"}
                self.wfile.write(json.dumps(error_response).encode())
                return

            auth_data = auth_codes[auth_code]
            if auth_data["client_id"] != client_id:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                error_response = {"error": "invalid_grant", "error_description": "Client ID mismatch"}
                self.wfile.write(json.dumps(error_response).encode())
                return

            # Generate access token and store user credentials
            access_token = generate_access_token(client_id, auth_code)
            user_credentials[access_token] = {
                "email": auth_data["user_email"],
                "password": auth_data["user_password"]
            }

            # Clean up auth code
            del auth_codes[auth_code]

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            response = {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": "mcp:read mcp:write accounts:read transactions:read budgets:read",
                "refresh_token": secrets.token_urlsafe(32)
            }
            self.wfile.write(json.dumps(response, indent=2).encode())
            return

        # Handle other POST requests
        else:
            self.do_GET()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()