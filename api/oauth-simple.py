"""
Simple OAuth registration endpoint for MCP client discovery
Minimal implementation to handle OAuth client registration
"""

import json
import secrets
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handler(event, context):
    """Handle OAuth registration and authorization requests"""
    try:
        headers = {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization"
        }

        path = event.get("path", "")
        method = event.get("httpMethod", "GET")

        logger.info(f"OAuth request: {method} {path}")

        # Handle preflight
        if method == "OPTIONS":
            return {
                "statusCode": 200,
                "headers": headers,
                "body": ""
            }

        # Handle OAuth client registration
        if "register" in path:
            # Parse request body if present
            request_data = {}
            if method == "POST":
                try:
                    body = event.get("body", "{}")
                    if body:
                        request_data = json.loads(body)
                except:
                    request_data = {}

            # Generate client credentials
            client_id = f"mcp_{secrets.token_urlsafe(16)}"
            client_secret = secrets.token_urlsafe(32)

            # Get redirect URIs
            redirect_uris = request_data.get("redirect_uris", ["https://cesar-money-mcp.vercel.app/oauth/callback"])

            # OAuth registration response
            response = {
                "client_id": client_id,
                "client_secret": client_secret,
                "client_id_issued_at": 1640995200,
                "client_secret_expires_at": 0,
                "redirect_uris": redirect_uris,
                "grant_types": ["authorization_code"],
                "response_types": ["code"],
                "scope": "mcp:read mcp:write",
                "token_endpoint_auth_method": "client_secret_basic"
            }

            logger.info(f"Registered OAuth client: {client_id}")

            return {
                "statusCode": 200,
                "headers": headers,
                "body": json.dumps(response)
            }

        # Handle authorization requests
        elif "authorize" in path:
            query_params = event.get("queryStringParameters", {}) or {}

            client_id = query_params.get("client_id", "unknown")
            redirect_uri = query_params.get("redirect_uri", "")
            state = query_params.get("state", "")

            # Generate authorization code
            auth_code = secrets.token_urlsafe(32)

            # Build callback URL
            callback_params = [f"code={auth_code}"]
            if state:
                callback_params.append(f"state={state}")

            callback_url = f"{redirect_uri}?{'&'.join(callback_params)}"

            return {
                "statusCode": 200,
                "headers": {"Content-Type": "text/html"},
                "body": f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>MCP Authorization</title>
                    <style>
                        body {{
                            font-family: system-ui, sans-serif;
                            max-width: 600px;
                            margin: 50px auto;
                            padding: 20px;
                            text-align: center;
                        }}
                        .btn {{
                            background: #0066cc;
                            color: white;
                            padding: 12px 24px;
                            border: none;
                            border-radius: 6px;
                            text-decoration: none;
                            display: inline-block;
                            margin: 10px;
                        }}
                    </style>
                </head>
                <body>
                    <h1>🔐 Authorize MCP Access</h1>
                    <p>Client requesting access: <code>{client_id}</code></p>
                    <p>Redirect URI: <code>{redirect_uri}</code></p>

                    <a href="{callback_url}" class="btn">✅ Authorize</a>
                    <a href="{redirect_uri}?error=access_denied&state={state}" class="btn" style="background: #cc0000;">❌ Deny</a>

                    <script>
                        // Auto-authorize after 3 seconds
                        setTimeout(function() {{
                            window.location.href = "{callback_url}";
                        }}, 3000);
                    </script>
                </body>
                </html>
                """
            }

        # Handle token exchange
        elif "token" in path:
            # Parse request body
            request_data = {}
            try:
                body = event.get("body", "")
                if body:
                    if body.startswith("{"):
                        request_data = json.loads(body)
                    else:
                        # Parse form data
                        for pair in body.split("&"):
                            if "=" in pair:
                                key, value = pair.split("=", 1)
                                request_data[key] = value
            except:
                pass

            grant_type = request_data.get("grant_type")
            code = request_data.get("code")
            client_id = request_data.get("client_id")

            if grant_type != "authorization_code":
                return {
                    "statusCode": 400,
                    "headers": headers,
                    "body": json.dumps({
                        "error": "unsupported_grant_type"
                    })
                }

            # Generate access token
            access_token = secrets.token_urlsafe(32)

            return {
                "statusCode": 200,
                "headers": headers,
                "body": json.dumps({
                    "access_token": access_token,
                    "token_type": "Bearer",
                    "expires_in": 3600,
                    "scope": "mcp:read mcp:write"
                })
            }

        else:
            return {
                "statusCode": 404,
                "headers": headers,
                "body": json.dumps({
                    "error": "not_found"
                })
            }

    except Exception as e:
        logger.error(f"OAuth handler error: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": "server_error",
                "error_description": str(e)
            })
        }