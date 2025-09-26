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

# Import the SQLite database module
try:
    from oauth_db import (
        store_oauth_client, get_oauth_client,
        store_auth_code, get_auth_code, delete_auth_code,
        store_access_token, get_access_token,
        cleanup_expired_tokens
    )
    DB_AVAILABLE = True
except ImportError as e:
    print(f"Database import failed: {e}")
    DB_AVAILABLE = False

def generate_client_credentials():
    """Generate new OAuth client credentials"""
    client_id = f"monarchmoney_mcp_{secrets.token_hex(8)}"
    client_secret = secrets.token_urlsafe(32)
    return client_id, client_secret

# In-memory fallback storage when database is not available
_fallback_clients = {}
_fallback_auth_codes = {}
_fallback_access_tokens = {}

def generate_auth_code(client_id, user_email=None, user_password=None):
    """Generate authorization code for client"""
    auth_code = secrets.token_urlsafe(32)
    if DB_AVAILABLE:
        store_auth_code(auth_code, client_id, user_email, user_password)
    else:
        _fallback_auth_codes[auth_code] = {
            "client_id": client_id,
            "user_email": user_email,
            "user_password": user_password
        }
    return auth_code

def generate_access_token(client_id, auth_code, user_email=None, user_password=None):
    """Generate access token for client and bind to user credentials"""
    access_token = secrets.token_urlsafe(32)
    if DB_AVAILABLE:
        store_access_token(access_token, client_id, auth_code, user_email, user_password)
    else:
        _fallback_access_tokens[access_token] = {
            "client_id": client_id,
            "auth_code": auth_code,
            "user_email": user_email,
            "user_password": user_password
        }
    return access_token

def get_user_credentials(access_token):
    """Get user credentials associated with an access token"""
    if DB_AVAILABLE:
        token_data = get_access_token(access_token)
        if token_data and token_data.get('user_email'):
            return {
                "email": token_data["user_email"],
                "password": token_data["user_password"]
            }
    else:
        token_data = _fallback_access_tokens.get(access_token)
        if token_data and token_data.get('user_email'):
            return {
                "email": token_data["user_email"],
                "password": token_data["user_password"]
            }
    return None

def validate_access_token(access_token):
    """Validate an access token and return associated data"""
    if DB_AVAILABLE:
        return get_access_token(access_token)
    else:
        return _fallback_access_tokens.get(access_token)

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
        path = self.path
        base_url = self.get_base_url()

        # OAuth 2.0 Authorization Server Metadata (RFC 8414)
        if ".well-known/oauth-authorization-server" in path:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
            self.end_headers()

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
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
            self.end_headers()

            response = {
                "resource": base_url,
                "authorization_servers": [base_url],
                "bearer_methods_supported": ["header"],
                "scopes_supported": ["mcp:read", "mcp:write", "accounts:read", "transactions:read", "budgets:read"]
            }
            self.wfile.write(json.dumps(response, indent=2).encode())
            return

        # Parse query parameters - handle malformed URLs with multiple question marks
        # This handles URLs like: /oauth?action=authorize?response_type=code&client_id=abc
        import re
        from urllib.parse import unquote, parse_qs

        # Debug logging setup
        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        logger.info(f"OAuth GET request - raw path: {path}")

        # Strategy: Extract the query part and normalize it
        # Handle malformed URLs with double question marks and URL encoding
        if '?' in path:
            # Split on first ?
            base_path, query_string = path.split('?', 1)

            # Replace any additional ? with & AND handle URL-encoded ? (%3F)
            # Also handle URL-encoded = (%3D) and & (%26)
            normalized_query = (query_string
                               .replace('?', '&')
                               .replace('%3F', '&')
                               .replace('%3D', '=')
                               .replace('%26', '&'))

            # Now parse normally
            query_params = parse_qs(normalized_query)
            logger.info(f"Original query: {query_string}")
            logger.info(f"Normalized query string: {normalized_query}")
        else:
            query_params = {}

        # Extract key parameters (parse_qs returns lists, so get first element)
        action = query_params.get('action', [''])[0]
        response_type = query_params.get('response_type', [''])[0]
        client_id = query_params.get('client_id', [''])[0]

        logger.info(f"Extracted params - action: '{action}', response_type: '{response_type}', client_id: '{client_id}'")
        logger.info(f"All parsed params: {query_params}")

        # OAuth authorization endpoint - handle incoming authorization request
        # This should trigger when Claude Code sends user for authorization
        # Check for authorization request FIRST (response_type=code + client_id present)
        # OR error redirects (error + client_id present)
        # This takes priority over action=authorize to handle malformed URLs
        error = query_params.get('error', [''])[0]
        if (response_type == "code" and client_id) or (error and client_id):
            logger.info(f"Detected authorization request - showing login form")
            redirect_uri = query_params.get('redirect_uri', [''])[0]
            state = query_params.get('state', [''])[0]
            scope = query_params.get('scope', [''])[0]

            # Auto-register the client if it doesn't exist (for demo purposes)
            if DB_AVAILABLE:
                client_data = get_oauth_client(client_id)
            else:
                client_data = _fallback_clients.get(client_id)

            if not client_data:
                client_secret = secrets.token_urlsafe(32)
                redirect_uris = [redirect_uri] if redirect_uri else []
                if DB_AVAILABLE:
                    store_oauth_client(client_id, client_secret, redirect_uris)
                else:
                    _fallback_clients[client_id] = {
                        "client_secret": client_secret,
                        "redirect_uris": redirect_uris
                    }

            # Check for error messages
            error_description = query_params.get('error_description', [''])[0]
            error_message = ""
            if error:
                if error == "invalid_credentials":
                    error_message = f'''<div style="background: #ffe6e6; color: #d00; padding: 10px; border-radius: 4px; margin-bottom: 20px; border: 1px solid #ffb3b3;">
                        <strong>⚠️ Authentication Failed:</strong> {unquote(error_description) if error_description else "Invalid Monarch Money credentials. Please check your email and password."}
                    </div>'''
                else:
                    error_message = f'''<div style="background: #ffe6e6; color: #d00; padding: 10px; border-radius: 4px; margin-bottom: 20px; border: 1px solid #ffb3b3;">
                        <strong>⚠️ Error:</strong> {unquote(error_description) if error_description else error}
                    </div>'''

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
    {error_message}
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

        <div class="form-group">
            <label for="mfa_secret">MFA Secret Key (if enabled):</label>
            <input type="text" name="mfa_secret" id="mfa_secret" placeholder="Your MFA secret key (base32 string from setup)">
            <small style="color: #666; font-size: 12px;">This is the secret key you got when setting up MFA, not the 6-digit code. Leave blank if you don't have MFA enabled.</small>
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

        # OAuth registration endpoint - generate new client credentials
        elif action == "register":
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
            self.end_headers()

            client_id, client_secret = generate_client_credentials()
            redirect_uris = [
                "https://api.agent.ai/api/v3/mcp/flow/redirect",
                "https://agent.ai/oauth/callback",
                "https://claude.ai/oauth/callback",
                "https://claude.ai/api/mcp/auth_callback",
                f"{base_url}/callback",
                "http://localhost:3000/callback",
                "mcp://oauth/callback"
            ]

            # Store client in database or fallback
            if DB_AVAILABLE:
                store_oauth_client(client_id, client_secret, redirect_uris)
            else:
                _fallback_clients[client_id] = {
                    "client_secret": client_secret,
                    "redirect_uris": redirect_uris
                }

            response = {
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uris": redirect_uris,
                "grant_types": ["authorization_code"],
                "response_types": ["code"],
                "scope": "mcp:read mcp:write accounts:read transactions:read budgets:read"
            }
            self.wfile.write(json.dumps(response, indent=2).encode())
            return


        # OAuth token endpoint (GET fallback)
        elif action == "token":
            parsed_url = urlparse(path)
            token_params = parse_qs(parsed_url.query)
            auth_code = token_params.get('code', [''])[0]
            client_id = token_params.get('client_id', [''])[0]

            if DB_AVAILABLE:
                auth_data = get_auth_code(auth_code)
            else:
                auth_data = _fallback_auth_codes.get(auth_code)

            if not auth_data:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                error_response = {"error": "invalid_grant", "error_description": "Invalid authorization code"}
                self.wfile.write(json.dumps(error_response).encode())
                return

            if auth_data["client_id"] != client_id:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
                self.end_headers()
                error_response = {"error": "invalid_grant", "error_description": "Client ID mismatch"}
                self.wfile.write(json.dumps(error_response).encode())
                return

            # Generate access token and store user credentials
            access_token = generate_access_token(
                client_id, auth_code,
                auth_data["user_email"],
                auth_data["user_password"]
            )

            # Clean up auth code
            if DB_AVAILABLE:
                delete_auth_code(auth_code)
            else:
                if auth_code in _fallback_auth_codes:
                    del _fallback_auth_codes[auth_code]

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
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

        # Default response
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

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

        # Debug logging
        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)
        logger.info(f"OAuth POST request - path: {path}")
        logger.info(f"OAuth POST action: {action}")
        logger.info(f"POST query params: {query_params}")

        # Handle OAuth authorization form submission
        if action == "process":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            form_data = parse_qs(post_data)

            email = form_data.get('email', [''])[0]
            password = form_data.get('password', [''])[0]
            mfa_secret = form_data.get('mfa_secret', [''])[0]
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
                    login_kwargs = {
                        "email": email,
                        "password": password,
                        "save_session": False,
                        "use_saved_session": False
                    }

                    # Add MFA secret key if provided
                    if mfa_secret and mfa_secret.strip():
                        login_kwargs["mfa_secret_key"] = mfa_secret.strip()

                    loop.run_until_complete(client.login(**login_kwargs))
                    # If we get here, credentials are valid
                    # Generate auth code with user credentials
                    auth_code = generate_auth_code(client_id, email, password)

                except Exception as login_error:
                    # Log the actual error for debugging
                    import logging
                    logging.basicConfig(level=logging.INFO)
                    logger = logging.getLogger(__name__)
                    logger.error(f"Monarch Money login failed: {str(login_error)}")
                    logger.error(f"Error type: {type(login_error).__name__}")

                    # Provide more specific error messages
                    error_msg = "Authentication failed"
                    error_str = str(login_error).lower()

                    if "mfa" in error_str or "two-factor" in error_str or "multi-factor" in error_str or "base32" in error_str:
                        if not mfa_secret:
                            error_msg = "MFA/2FA is required for your account. Please enter your MFA secret key (the base32 string you got when setting up your authenticator app)."
                        else:
                            error_msg = "Invalid MFA secret key. Please check that you entered the correct base32 secret key from your MFA setup."
                    elif "invalid" in error_str or "unauthorized" in error_str:
                        error_msg = "Invalid email or password. Please check your Monarch Money credentials."
                    elif "network" in error_str or "timeout" in error_str:
                        error_msg = "Network error connecting to Monarch Money. Please try again."
                    elif "rate" in error_str or "limit" in error_str:
                        error_msg = "Too many login attempts. Please wait and try again."
                    else:
                        error_msg = f"Login failed: {str(login_error)}"

                    # Login failed - redirect back with error
                    from urllib.parse import quote
                    error_redirect = f"/oauth?action=authorize&client_id={client_id}&redirect_uri={redirect_uri}&state={state}&error=invalid_credentials&error_description={quote(error_msg)}"
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

            if DB_AVAILABLE:
                auth_data = get_auth_code(auth_code)
            else:
                auth_data = _fallback_auth_codes.get(auth_code)

            if not auth_data:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                error_response = {"error": "invalid_grant", "error_description": "Invalid authorization code"}
                self.wfile.write(json.dumps(error_response).encode())
                return

            if auth_data["client_id"] != client_id:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                error_response = {"error": "invalid_grant", "error_description": "Client ID mismatch"}
                self.wfile.write(json.dumps(error_response).encode())
                return

            # Generate access token and store user credentials
            access_token = generate_access_token(
                client_id, auth_code,
                auth_data["user_email"],
                auth_data["user_password"]
            )

            # Clean up auth code
            if DB_AVAILABLE:
                delete_auth_code(auth_code)
            else:
                if auth_code in _fallback_auth_codes:
                    del _fallback_auth_codes[auth_code]

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

        # Handle OAuth registration via POST (Claude Code may send POST)
        elif action == "register":
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
            self.end_headers()

            base_url = self.get_base_url()
            client_id, client_secret = generate_client_credentials()
            oauth_clients[client_id] = {
                "client_secret": client_secret,
                "redirect_uris": [
                    "https://api.agent.ai/api/v3/mcp/flow/redirect",
                    "https://agent.ai/oauth/callback",
                    "https://claude.ai/oauth/callback",
                    "https://claude.ai/api/mcp/auth_callback",
                    f"{base_url}/callback",
                    "http://localhost:3000/callback",
                    "mcp://oauth/callback"
                ],
                "created_at": json.dumps({"timestamp": "2024-09-26T18:21:12Z"})
            }

            response = {
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uris": oauth_clients[client_id]["redirect_uris"],
                "grant_types": ["authorization_code"],
                "response_types": ["code"],
                "scope": "mcp:read mcp:write accounts:read transactions:read budgets:read"
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