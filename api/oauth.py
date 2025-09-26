"""
OAuth registration and authorization endpoints for MCP client discovery
Implements the OAuth endpoints that MCP clients expect to find
"""

import json
import os
import secrets
import logging
from typing import Dict, Any
from urllib.parse import urlencode

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
BASE_URL = "https://cesar-money-mcp.vercel.app"  # Fixed base URL
API_KEY = os.getenv("API_KEY")

def handle_client_registration(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle OAuth client registration requests"""
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization"
    }

    method = event.get("httpMethod", "GET")

    if method == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": headers,
            "body": ""
        }

    # Parse request body for POST requests
    request_data = {}
    if method == "POST":
        try:
            body = event.get("body", "{}")
            if isinstance(body, str):
                request_data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            pass

    # Generate a client ID and secret
    client_id = f"mcp_{secrets.token_urlsafe(16)}"
    client_secret = secrets.token_urlsafe(32)

    # OAuth client registration response
    registration_response = {
        "client_id": client_id,
        "client_secret": client_secret,
        "client_id_issued_at": 1640995200,  # Unix timestamp
        "client_secret_expires_at": 0,  # Never expires
        "authorization_endpoint": f"{BASE_URL}/oauth/authorize",
        "token_endpoint": f"{BASE_URL}/oauth/token",
        "grant_types": ["authorization_code"],
        "response_types": ["code"],
        "redirect_uris": request_data.get("redirect_uris", [f"{BASE_URL}/oauth/callback"]),
        "scope": "mcp:read mcp:write",
        "token_endpoint_auth_method": "client_secret_basic"
    }

    return {
        "statusCode": 200,
        "headers": headers,
        "body": json.dumps(registration_response)
    }

def handle_authorization_request(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle OAuth authorization requests"""
    # Get query parameters
    query_params = event.get("queryStringParameters", {}) or {}

    client_id = query_params.get("client_id")
    redirect_uri = query_params.get("redirect_uri")
    state = query_params.get("state")
    scope = query_params.get("scope", "mcp:read mcp:write")

    if not client_id or not redirect_uri:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "text/html"},
            "body": """
            <html>
                <body>
                    <h1>OAuth Error</h1>
                    <p>Missing required parameters: client_id and redirect_uri</p>
                </body>
            </html>
            """
        }

    # Generate authorization code
    auth_code = secrets.token_urlsafe(32)

    # In a real implementation, you'd store this code and associate it with the client
    # For now, we'll redirect with the code immediately

    callback_params = {
        "code": auth_code,
        "state": state
    }

    callback_url = f"{redirect_uri}?{urlencode(callback_params)}"

    # Return authorization page that auto-redirects
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "text/html"},
        "body": f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>MCP OAuth Authorization</title>
            <style>
                body {{
                    font-family: -apple-system, system-ui, sans-serif;
                    max-width: 600px;
                    margin: 100px auto;
                    padding: 20px;
                    text-align: center;
                }}
                .container {{
                    background: white;
                    border-radius: 10px;
                    padding: 40px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }}
                .btn {{
                    background: #667eea;
                    color: white;
                    padding: 12px 24px;
                    border: none;
                    border-radius: 6px;
                    text-decoration: none;
                    display: inline-block;
                    margin: 10px;
                    cursor: pointer;
                }}
                .btn:hover {{
                    background: #5a67d8;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔐 Authorize MCP Client</h1>
                <p>A Model Context Protocol client is requesting access to your Monarch Money data.</p>

                <div style="background: #f7fafc; padding: 20px; border-radius: 6px; margin: 20px 0;">
                    <strong>Client ID:</strong> {client_id}<br>
                    <strong>Requested Scope:</strong> {scope}<br>
                    <strong>Redirect URI:</strong> {redirect_uri}
                </div>

                <p>Click "Authorize" to grant access or "Deny" to reject the request.</p>

                <a href="{callback_url}" class="btn">✅ Authorize</a>
                <a href="{redirect_uri}?error=access_denied&state={state}" class="btn" style="background: #e53e3e;">❌ Deny</a>

                <script>
                    // Auto-authorize for MCP clients (remove this for manual approval)
                    setTimeout(function() {{
                        window.location.href = "{callback_url}";
                    }}, 2000);
                </script>
            </div>
        </body>
        </html>
        """
    }

def handle_token_request(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle OAuth token exchange requests"""
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization"
    }

    if event.get("httpMethod") == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": headers,
            "body": ""
        }

    # Parse request data
    request_data = {}
    try:
        body = event.get("body", "")
        if body:
            if body.startswith("{"):
                request_data = json.loads(body)
            else:
                # Parse form data
                import urllib.parse
                parsed = urllib.parse.parse_qs(body)
                request_data = {k: v[0] if isinstance(v, list) and v else v for k, v in parsed.items()}
    except Exception as e:
        logger.error(f"Error parsing request body: {e}")
        request_data = {}

    grant_type = request_data.get("grant_type")
    code = request_data.get("code")
    client_id = request_data.get("client_id")

    if grant_type != "authorization_code" or not code or not client_id:
        return {
            "statusCode": 400,
            "headers": headers,
            "body": json.dumps({
                "error": "invalid_request",
                "error_description": "Missing or invalid parameters"
            })
        }

    # Generate access token (in real implementation, validate the code)
    access_token = API_KEY  # Use our API key as the access token

    token_response = {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": "mcp:read mcp:write"
    }

    return {
        "statusCode": 200,
        "headers": headers,
        "body": json.dumps(token_response)
    }

def handler(event, context):
    """Main handler for OAuth endpoints"""
    try:
        path = event.get("path", "").strip("/")
        method = event.get("httpMethod", "GET")

        logger.info(f"OAuth request: {method} {path}")

        # Route to appropriate handler
        if "register" in path:
            return handle_client_registration(event)
        elif "authorize" in path:
            return handle_authorization_request(event)
        elif "token" in path:
            return handle_token_request(event)
        else:
            logger.warning(f"Unknown OAuth path: {path}")
            return {
                "statusCode": 404,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({
                    "error": "not_found",
                    "error_description": f"OAuth endpoint not found: {path}"
                })
            }
    except Exception as e:
        logger.error(f"OAuth handler error: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": "server_error",
                "error_description": f"Internal server error: {str(e)}"
            })
        }