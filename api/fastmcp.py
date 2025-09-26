"""
FastMCP Vercel Handler with OAuth Support
HTTP wrapper for FastMCP OAuth server
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

async def call_fastmcp_tool(tool_name: str, arguments: dict):
    """Call a FastMCP tool directly"""
    try:
        # Import the OAuth FastMCP server
        from fastmcp_oauth_server import mcp, oauth_register, oauth_authorize, oauth_token, get_accounts, get_transactions, get_budgets

        # Map tool names to functions
        tool_map = {
            "oauth_register": oauth_register,
            "oauth_authorize": oauth_authorize,
            "oauth_token": oauth_token,
            "get_accounts": get_accounts,
            "get_transactions": get_transactions,
            "get_budgets": get_budgets
        }

        if tool_name not in tool_map:
            raise ValueError(f"Unknown tool: {tool_name}")

        # Call the tool function
        tool_func = tool_map[tool_name]
        result = await tool_func(**arguments)

        return {"success": True, "result": result}

    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        return {"success": False, "error": str(e)}

def handler(event, context):
    """Vercel handler for FastMCP OAuth tools"""
    try:
        headers = {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization"
        }

        # Handle preflight
        if event.get("httpMethod") == "OPTIONS":
            return {
                "statusCode": 200,
                "headers": headers,
                "body": ""
            }

        # Parse request body
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
                    "error": "Invalid JSON in request body"
                })
            }

        # Extract tool call information
        tool_name = request_data.get("name")
        arguments = request_data.get("arguments", {})

        if not tool_name:
            return {
                "statusCode": 400,
                "headers": headers,
                "body": json.dumps({
                    "error": "Missing 'name' field for tool call"
                })
            }

        # Execute the tool
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(call_fastmcp_tool(tool_name, arguments))
        finally:
            loop.close()

        # Return result
        if result["success"]:
            return {
                "statusCode": 200,
                "headers": headers,
                "body": json.dumps({
                    "content": [{"type": "text", "text": result["result"]}]
                })
            }
        else:
            return {
                "statusCode": 500,
                "headers": headers,
                "body": json.dumps({
                    "error": result["error"]
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