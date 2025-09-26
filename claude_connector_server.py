#!/usr/bin/env python3
"""
Claude Custom Connector Compatible MCP Server
Designed for remote deployment and Claude integration
Follows MCP 2025-06-18 specification
"""

import os
import sys
import asyncio
import json
import logging
from typing import Dict, Any, List
from datetime import datetime, timezone
import traceback

# FastAPI for HTTP server
try:
    from fastapi import FastAPI, HTTPException, Request, Depends, Header
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    import uvicorn
except ImportError:
    print("FastAPI not installed. Install with: pip install fastapi uvicorn")
    sys.exit(1)

# Import our MCP server and OAuth manager
from mcp_server_compliant import MonarchMCPServer, config
from secure_oauth import SecureOAuthManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("monarchmoney-claude-connector")

# Global instances
oauth_manager = SecureOAuthManager()
mcp_server_instance = MonarchMCPServer()

# FastAPI app
app = FastAPI(
    title="Monarch Money MCP Server",
    description="Model Context Protocol server for Monarch Money - Compatible with Claude Custom Connectors",
    version="1.0.0"
)

# CORS configuration for Claude compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify Claude's domains
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# OAuth 2.1 Authorization Server Metadata (RFC 8414)
@app.get("/.well-known/oauth-authorization-server")
async def oauth_metadata():
    """OAuth 2.1 authorization server metadata"""
    base_url = os.getenv("BASE_URL", "https://your-mcp-server.com")

    return {
        "issuer": base_url,
        "authorization_endpoint": f"{base_url}/oauth/authorize",
        "token_endpoint": f"{base_url}/oauth/token",
        "registration_endpoint": f"{base_url}/oauth/register",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["client_secret_post"],
        "scopes_supported": ["accounts:read", "transactions:read", "budgets:read"]
    }

# OAuth 2.0 Protected Resource Metadata (RFC 9728)
@app.get("/.well-known/oauth-protected-resource")
async def protected_resource_metadata():
    """OAuth 2.0 protected resource metadata"""
    base_url = os.getenv("BASE_URL", "https://your-mcp-server.com")

    return {
        "resource": base_url,
        "authorization_servers": [base_url],
        "bearer_methods_supported": ["header"],
        "scopes_supported": ["accounts:read", "transactions:read", "budgets:read"]
    }

# OAuth 2.1 Endpoints
@app.post("/oauth/register")
async def oauth_register(request: Request):
    """OAuth 2.1 Dynamic Client Registration"""
    try:
        body = await request.json()
        redirect_uris = body.get("redirect_uris", [])

        client_info = oauth_manager.register_client(redirect_uris)
        return client_info

    except Exception as e:
        logger.error(f"Client registration error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/oauth/authorize")
async def oauth_authorize(
    response_type: str,
    client_id: str,
    redirect_uri: str = None,
    state: str = None,
    scope: str = None
):
    """OAuth 2.1 Authorization Endpoint - Returns login form"""
    if response_type != "code":
        raise HTTPException(status_code=400, detail="Unsupported response type")

    # Return HTML login form
    form_html = f"""
    <!DOCTYPE html>
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
            <strong>Scope:</strong> {scope or 'accounts:read transactions:read budgets:read'}
        </div>
        <form method="post" action="/oauth/authorize">
            <input type="hidden" name="client_id" value="{client_id}">
            <input type="hidden" name="redirect_uri" value="{redirect_uri or ''}">
            <input type="hidden" name="state" value="{state or ''}">
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
            Your credentials are verified against Monarch Money and are stored securely.
        </p>
    </body>
    </html>
    """

    return JSONResponse(content=form_html, media_type="text/html")

@app.post("/oauth/authorize")
async def oauth_authorize_post(request: Request):
    """Process authorization form submission"""
    try:
        form_data = await request.form()

        client_id = form_data["client_id"]
        email = form_data["email"]
        password = form_data["password"]
        redirect_uri = form_data.get("redirect_uri")
        state = form_data.get("state")

        # Create authorization code
        auth_code = await oauth_manager.authorize(client_id, email, password)

        # Redirect back to client
        if redirect_uri:
            callback_url = f"{redirect_uri}?code={auth_code}"
            if state:
                callback_url += f"&state={state}"

            return JSONResponse(
                content={"redirect_url": callback_url},
                status_code=302,
                headers={"Location": callback_url}
            )
        else:
            return {"code": auth_code}

    except Exception as e:
        logger.error(f"Authorization error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/oauth/token")
async def oauth_token(request: Request):
    """OAuth 2.1 Token Endpoint"""
    try:
        form_data = await request.form()

        grant_type = form_data.get("grant_type")
        if grant_type != "authorization_code":
            raise HTTPException(status_code=400, detail="Unsupported grant type")

        code = form_data["code"]
        client_id = form_data["client_id"]
        client_secret = form_data["client_secret"]

        token_response = oauth_manager.exchange_code_for_token(code, client_id, client_secret)
        return token_response

    except Exception as e:
        logger.error(f"Token exchange error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# MCP Protocol Endpoints
async def get_bearer_token(authorization: str = Header(None)) -> str:
    """Extract and validate bearer token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = authorization.split(" ", 1)[1]
    token_data = oauth_manager.validate_token(token)

    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return token

@app.post("/mcp/rpc")
async def mcp_rpc(request: Request, token: str = Depends(get_bearer_token)):
    """MCP JSON-RPC endpoint"""
    try:
        body = await request.json()

        method = body.get("method")
        params = body.get("params", {})
        request_id = body.get("id")

        logger.info(f"MCP RPC call: {method}")

        if method == "initialize":
            response = {
                "jsonrpc": "2.0",
                "result": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {
                        "tools": {
                            "listChanged": False
                        }
                    },
                    "serverInfo": {
                        "name": config.server_name,
                        "version": config.server_version,
                        "description": "Monarch Money MCP Server for Claude Custom Connectors"
                    }
                },
                "id": request_id
            }

        elif method == "tools/list":
            # Get tools from our MCP server
            tools = await mcp_server_instance.server._tools_handler()

            response = {
                "jsonrpc": "2.0",
                "result": {
                    "tools": [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "inputSchema": tool.inputSchema
                        }
                        for tool in tools
                    ]
                },
                "id": request_id
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if not tool_name:
                raise HTTPException(status_code=400, detail="Missing tool name")

            # Call the tool using our MCP server
            result = await mcp_server_instance.server._tools_call_handler(tool_name, arguments)

            response = {
                "jsonrpc": "2.0",
                "result": {
                    "content": [{"type": "text", "text": content.text} for content in result]
                },
                "id": request_id
            }

        else:
            response = {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                },
                "id": request_id
            }

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MCP RPC error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")

        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            },
            "id": body.get("id") if 'body' in locals() else None
        }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": config.server_version,
        "protocol_version": config.protocol_version
    }

@app.get("/")
async def root():
    """Root endpoint with server information"""
    base_url = os.getenv("BASE_URL", "https://your-mcp-server.com")

    return {
        "name": config.server_name,
        "version": config.server_version,
        "protocol_version": config.protocol_version,
        "description": "Monarch Money MCP Server compatible with Claude Custom Connectors",
        "endpoints": {
            "mcp_rpc": f"{base_url}/mcp/rpc",
            "oauth_register": f"{base_url}/oauth/register",
            "oauth_authorize": f"{base_url}/oauth/authorize",
            "oauth_token": f"{base_url}/oauth/token",
            "health": f"{base_url}/health"
        },
        "oauth_metadata": f"{base_url}/.well-known/oauth-authorization-server",
        "documentation": "https://github.com/your-username/monarchmoney-mcp"
    }

if __name__ == "__main__":
    # Configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "false").lower() == "true"

    logger.info(f"Starting Monarch Money MCP Server for Claude Custom Connectors")
    logger.info(f"Host: {host}:{port}")
    logger.info(f"Protocol Version: {config.protocol_version}")

    # Run the server
    uvicorn.run("claude_connector_server:app", host=host, port=port, reload=reload)