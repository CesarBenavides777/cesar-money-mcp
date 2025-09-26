"""
MCP Server Discovery Endpoint
Provides server capabilities and OAuth endpoints for MCP client discovery
"""

import json
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handler(event, context):
    """Handle MCP server discovery requests"""
    try:
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

        # MCP server discovery response
        base_url = "https://cesar-money-mcp.vercel.app"

        discovery_response = {
            "server_info": {
                "name": "Monarch Money MCP Server",
                "version": "1.0.0",
                "description": "Access your Monarch Money financial data via MCP",
                "protocol_version": "2024-11-05"
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
                "mcp": f"{base_url}/api",
                "tools": f"{base_url}/tools/call",
                "oauth_register": f"{base_url}/oauth/register",
                "oauth_authorize": f"{base_url}/oauth/authorize",
                "oauth_token": f"{base_url}/oauth/token"
            },
            "tools": [
                {
                    "name": "get_accounts",
                    "description": "Get all Monarch Money accounts with balances",
                    "parameters": {
                        "access_token": {
                            "type": "string",
                            "description": "OAuth access token",
                            "required": True
                        }
                    }
                },
                {
                    "name": "get_transactions",
                    "description": "Get Monarch Money transactions with filtering",
                    "parameters": {
                        "access_token": {
                            "type": "string",
                            "description": "OAuth access token",
                            "required": True
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Start date in YYYY-MM-DD format",
                            "required": False
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date in YYYY-MM-DD format",
                            "required": False
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum transactions to return",
                            "required": False,
                            "default": 100
                        }
                    }
                }
            ]
        }

        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps(discovery_response, indent=2)
        }

    except Exception as e:
        logger.error(f"Discovery endpoint error: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": "server_error",
                "error_description": f"Discovery failed: {str(e)}"
            })
        }