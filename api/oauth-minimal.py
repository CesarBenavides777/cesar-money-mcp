"""
Minimal OAuth endpoint for MCP client registration
No external dependencies, basic functionality only
"""

def handler(event, context):
    """Minimal OAuth handler"""
    try:
        import json
        import random
        import string

        # Generate random strings
        def random_string(length=16):
            return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

        headers = {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization"
        }

        method = event.get("httpMethod", "GET")
        path = event.get("path", "")

        # Handle preflight
        if method == "OPTIONS":
            return {
                "statusCode": 200,
                "headers": headers,
                "body": ""
            }

        # OAuth client registration
        if "register" in path:
            client_id = f"mcp_{random_string(16)}"
            client_secret = random_string(32)

            response = {
                "client_id": client_id,
                "client_secret": client_secret,
                "client_id_issued_at": 1640995200,
                "client_secret_expires_at": 0,
                "redirect_uris": ["https://cesar-money-mcp.vercel.app/oauth/callback"],
                "grant_types": ["authorization_code"],
                "response_types": ["code"],
                "scope": "mcp:read mcp:write",
                "token_endpoint_auth_method": "client_secret_basic"
            }

            return {
                "statusCode": 200,
                "headers": headers,
                "body": json.dumps(response)
            }

        # Simple authorization
        elif "authorize" in path:
            auth_code = random_string(32)

            return {
                "statusCode": 200,
                "headers": {"Content-Type": "text/html"},
                "body": f"""
                <html>
                <body>
                    <h1>OAuth Authorization</h1>
                    <p>Authorization Code: {auth_code}</p>
                    <script>
                        setTimeout(function() {{
                            window.location.href = "https://example.com/callback?code={auth_code}";
                        }}, 2000);
                    </script>
                </body>
                </html>
                """
            }

        # Token endpoint
        elif "token" in path:
            access_token = random_string(32)

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

        # Default response
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({
                "message": "OAuth endpoint active",
                "path": path,
                "method": method
            })
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "text/plain"},
            "body": f"Error: {str(e)}"
        }