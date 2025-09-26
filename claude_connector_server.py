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

# Import our configuration from the main server
import os
import sys
sys.path.append(os.path.dirname(__file__))

# Simple config for the connector
class SimpleConfig:
    def __init__(self):
        self.server_name = "Monarch Money MCP Server"
        self.server_version = "1.0.0"
        self.protocol_version = "2025-06-18"

config = SimpleConfig()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("monarchmoney-claude-connector")

# Global instances - removed complex OAuth manager for Claude compatibility

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
    base_url = os.getenv("BASE_URL", "https://cesar-money-mcp.vercel.app")

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
    base_url = os.getenv("BASE_URL", "https://cesar-money-mcp.vercel.app")

    return {
        "resource": base_url,
        "authorization_servers": [base_url],
        "bearer_methods_supported": ["header"],
        "scopes_supported": ["accounts:read", "transactions:read", "budgets:read"]
    }

# Simplified OAuth for Claude Custom Connectors
@app.post("/oauth/register")
async def oauth_register(request: Request):
    """Simplified OAuth client registration for Claude"""
    try:
        # For Claude, we can use a simplified registration
        return {
            "client_id": "claude-mcp-client",
            "client_secret": "mcp-secret-2024",
            "redirect_uris": [
                "https://claude.ai/oauth/callback",
                "https://claude.ai/api/mcp/auth_callback"
            ],
            "grant_types": ["authorization_code"],
            "response_types": ["code"]
        }

    except Exception as e:
        logger.error(f"Client registration error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/oauth/authorize")
async def oauth_authorize(
    response_type: str = "code",
    client_id: str = "claude-mcp-client",
    redirect_uri: str = None,
    state: str = None,
    scope: str = "read"
):
    """Simplified OAuth Authorization for Claude"""
    # Claude usually handles this automatically, so we can return a simple auth code
    # In production, you'd want proper user consent flow

    try:
        # For Claude integration, we can auto-approve with user's stored credentials
        auth_code = "auto_generated_code_for_claude_" + str(int(datetime.now().timestamp()))

        if redirect_uri:
            callback_url = f"{redirect_uri}?code={auth_code}"
            if state:
                callback_url += f"&state={state}"

            return {
                "redirect_url": callback_url,
                "code": auth_code
            }
        else:
            return {"code": auth_code}

    except Exception as e:
        logger.error(f"Authorization error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

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
    """Simplified OAuth Token Endpoint for Claude"""
    try:
        form_data = await request.form()

        grant_type = form_data.get("grant_type")
        code = form_data.get("code")
        client_id = form_data.get("client_id", "claude-mcp-client")
        client_secret = form_data.get("client_secret", "mcp-secret-2024")

        # Validate the code format (should start with our prefix)
        if not code or not code.startswith("auto_generated_code_for_claude_"):
            raise HTTPException(status_code=400, detail="Invalid authorization code")

        # Return a simple access token for Claude
        access_token = f"mcp_access_token_{int(datetime.now().timestamp())}"

        return {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": 3600,  # 1 hour
            "scope": "read"
        }

    except Exception as e:
        logger.error(f"Token exchange error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# MCP Protocol Endpoints
async def get_bearer_token(authorization: str = Header(None)) -> str:
    """Extract and validate bearer token for Claude"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = authorization.split(" ", 1)[1]

    # Simple validation for Claude tokens
    if not token.startswith("mcp_access_token_"):
        raise HTTPException(status_code=401, detail="Invalid token format")

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
            # Return tools list directly for Claude
            response = {
                "jsonrpc": "2.0",
                "result": {
                    "tools": [
                        {
                            "name": "get_accounts",
                            "description": "Get all Monarch Money accounts with balances and details",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        },
                        {
                            "name": "get_transactions",
                            "description": "Get Monarch Money transactions with optional filtering",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format"},
                                    "end_date": {"type": "string", "description": "End date in YYYY-MM-DD format"},
                                    "limit": {"type": "integer", "description": "Maximum number of transactions", "default": 100},
                                    "account_id": {"type": "string", "description": "Optional account ID filter"}
                                },
                                "required": []
                            }
                        },
                        {
                            "name": "get_budgets",
                            "description": "Get Monarch Money budget information and categories",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        }
                    ]
                },
                "id": request_id
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if not tool_name:
                raise HTTPException(status_code=400, detail="Missing tool name")

            # Import and call the tools directly
            sys.path.append(os.path.dirname(__file__))
            import fastmcp_server

            # Call the appropriate tool function
            if tool_name == "get_accounts":
                result_text = await fastmcp_server.get_accounts()
            elif tool_name == "get_transactions":
                result_text = await fastmcp_server.get_transactions(**arguments)
            elif tool_name == "get_budgets":
                result_text = await fastmcp_server.get_budgets()
            elif tool_name == "get_spending_plan":
                result_text = await fastmcp_server.get_spending_plan(**arguments)
            elif tool_name == "get_account_history":
                result_text = await fastmcp_server.get_account_history(**arguments)
            else:
                raise HTTPException(status_code=400, detail=f"Unknown tool: {tool_name}")

            response = {
                "jsonrpc": "2.0",
                "result": {
                    "content": [{"type": "text", "text": result_text}]
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
    base_url = os.getenv("BASE_URL", "https://cesar-money-mcp.vercel.app")

    return {
        "name": "Monarch Money MCP Server",
        "version": "1.0.0",
        "description": "Monarch Money MCP Server for Claude Custom Connectors",
        "mcp_endpoint": f"{base_url}/mcp",
        "endpoints": {
            "mcp_rpc": f"{base_url}/mcp/rpc",
            "oauth_authorize": f"{base_url}/oauth/authorize",
            "oauth_token": f"{base_url}/oauth/token",
            "health": f"{base_url}/health"
        },
        "oauth_metadata": f"{base_url}/.well-known/oauth-authorization-server",
        "instructions": {
            "claude_setup": f"Add this URL to Claude Custom Connectors: {base_url}/mcp",
            "oauth_client_id": "claude-mcp-client",
            "oauth_client_secret": "mcp-secret-2024"
        }
    }

# Main MCP endpoint that Claude expects
@app.get("/mcp")
async def mcp_endpoint():
    """Main MCP endpoint for Claude Custom Connectors"""
    base_url = os.getenv("BASE_URL", "https://cesar-money-mcp.vercel.app")

    return {
        "version": "2025-06-18",
        "capabilities": {
            "tools": True,
            "resources": False,
            "prompts": False
        },
        "serverInfo": {
            "name": "Monarch Money MCP Server",
            "version": "1.0.0"
        },
        "endpoints": {
            "rpc": f"{base_url}/mcp/rpc"
        },
        "authentication": {
            "type": "oauth2",
            "authorization_url": f"{base_url}/oauth/authorize",
            "token_url": f"{base_url}/oauth/token"
        }
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