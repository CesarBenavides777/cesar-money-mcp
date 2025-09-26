"""
FastMCP Vercel Handler
Simple wrapper to run FastMCP server on Vercel
"""

import os
import sys
import asyncio
import json
import logging

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handler(event, context):
    """Vercel handler for FastMCP server"""
    try:
        # Import our FastMCP server
        from fastmcp_server import mcp

        headers = {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-API-Key"
        }

        # Handle preflight
        if event.get("httpMethod") == "OPTIONS":
            return {
                "statusCode": 200,
                "headers": headers,
                "body": ""
            }

        # Simple authentication check
        API_KEY = os.getenv("API_KEY")
        if API_KEY:
            auth_header = event.get("headers", {}).get("authorization", "")
            api_key_header = event.get("headers", {}).get("x-api-key", "")

            authenticated = False
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                if token == API_KEY:
                    authenticated = True
            elif api_key_header == API_KEY:
                authenticated = True

            if not authenticated:
                return {
                    "statusCode": 401,
                    "headers": headers,
                    "body": json.dumps({
                        "error": "Authentication required",
                        "message": "Provide Authorization: Bearer <token> or X-API-Key header"
                    })
                }

        # For Vercel, we'll create a simple info endpoint
        # FastMCP is designed for STDIO, not HTTP, so this is just basic info
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({
                "name": "Monarch Money MCP Server",
                "description": "FastMCP-based server for Monarch Money data",
                "protocol": "Model Context Protocol",
                "transport": "STDIO (not HTTP)",
                "message": "This server is designed to run with STDIO transport. For HTTP access, use the /api endpoint instead.",
                "tools": [
                    "get_accounts",
                    "get_transactions",
                    "get_budgets",
                    "get_spending_plan",
                    "get_account_history"
                ],
                "instructions": "Connect using MCP client with STDIO transport to: uv run fastmcp_server.py"
            })
        }

    except Exception as e:
        logger.error(f"FastMCP handler error: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": "Internal server error",
                "message": str(e)
            })
        }