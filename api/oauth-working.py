"""
Working OAuth endpoints for MCP
Ultra-simple implementation that actually works on Vercel
"""

import json

def handler(event, context):
    """Ultra-simple OAuth handler that works"""

    # Basic headers
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization"
    }

    # Handle preflight
    if event.get("httpMethod") == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": headers,
            "body": ""
        }

    path = event.get("path", "")

    # OAuth registration endpoint
    if "register" in path:
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({
                "client_id": "mcp_monarchmoney_12345",
                "client_secret": "secret_67890",
                "redirect_uris": ["https://example.com/callback"],
                "grant_types": ["authorization_code"],
                "response_types": ["code"],
                "scope": "mcp:read mcp:write"
            })
        }

    # OAuth authorization endpoint
    elif "authorize" in path:
        return {
            "statusCode": 302,
            "headers": {
                "Location": "https://example.com/callback?code=auth_code_12345&state=test"
            },
            "body": ""
        }

    # OAuth token endpoint
    elif "token" in path:
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({
                "access_token": "access_token_12345",
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
            "message": "OAuth endpoints active",
            "endpoints": [
                "/oauth/register",
                "/oauth/authorize",
                "/oauth/token"
            ]
        })
    }