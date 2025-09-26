"""
MCP Protocol Server for Monarch Money (Vercel HTTP Transport)
HTTP wrapper for the official MCP SDK server
"""

import json
import os
import logging
import asyncio
import io
from typing import Dict, Any

# Import MCP types and server
import mcp.types as types
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server

# Import our server logic
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
API_KEY = os.getenv("API_KEY")

def verify_auth(headers: Dict[str, str]) -> bool:
    """Verify API key authentication"""
    if not API_KEY:
        logger.error("API_KEY not configured")
        return False

    provided_key = headers.get("x-api-key") or headers.get("X-API-Key")
    if not provided_key:
        logger.warning("No API key provided")
        return False

    import hmac
    return hmac.compare_digest(provided_key, API_KEY)

async def create_mcp_server():
    """Create and configure the MCP server"""
    from mcp_server import server as mcp_server
    return mcp_server

async def handle_mcp_request(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle MCP protocol requests over HTTP"""
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, X-API-Key"
    }

    # Handle preflight
    if event.get("httpMethod") == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": headers,
            "body": ""
        }

    # Verify authentication
    request_headers = event.get("headers", {})
    if not verify_auth(request_headers):
        return {
            "statusCode": 401,
            "headers": headers,
            "body": json.dumps({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32600,
                    "message": "Authentication required. Provide X-API-Key header."
                },
                "id": None
            })
        }

    # Parse JSON-RPC request
    try:
        body = event.get("body", "{}")
        if isinstance(body, str):
            request_data = json.loads(body)
        else:
            request_data = body
    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "headers": headers,
            "body": json.dumps({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32700,
                    "message": "Parse error"
                },
                "id": None
            })
        }

    # Extract request components
    method = request_data.get("method")
    params = request_data.get("params", {})
    request_id = request_data.get("id")

    logger.info(f"MCP request: {method}")

    try:
        # Create MCP server instance
        mcp_server = await create_mcp_server()

        # Handle different MCP methods
        if method == "initialize":
            # Handle initialization
            result = {
                "protocolVersion": params.get("protocolVersion", "2024-11-05"),
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "monarchmoney-mcp",
                    "version": "1.0.0"
                }
            }

        elif method == "tools/list":
            # Get tools from the MCP server
            tools = await mcp_server._list_tools_handler()
            result = {
                "tools": [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.inputSchema
                    }
                    for tool in tools
                ]
            }

        elif method == "tools/call":
            # Call a tool
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})

            if not tool_name:
                raise ValueError("Tool name is required")

            # Execute the tool
            tool_result = await mcp_server._call_tool_handler(tool_name, tool_args)

            result = {
                "content": [
                    {
                        "type": content.type,
                        "text": content.text
                    }
                    for content in tool_result
                ]
            }

        elif method == "initialized":
            # Acknowledge initialization
            result = {}

        else:
            return {
                "statusCode": 400,
                "headers": headers,
                "body": json.dumps({
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    },
                    "id": request_id
                })
            }

        # Return successful response
        response_body = {
            "jsonrpc": "2.0",
            "result": result,
            "id": request_id
        }

        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps(response_body)
        }

    except Exception as e:
        logger.error(f"MCP request error: {e}")
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                },
                "id": request_id
            })
        }

def handler(event, context):
    """Vercel handler for MCP requests"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        return loop.run_until_complete(handle_mcp_request(event))
    finally:
        loop.close()