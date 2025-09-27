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
    allow_origins=["https://claude.ai", "https://claude.com", "http://localhost:*"],  # Claude domains + localhost for testing
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
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
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none"],
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

# Dynamic Client Registration (RFC 7591) - Required for Claude Custom Connectors
@app.post("/oauth/register")
async def oauth_register(request: Request):
    """Dynamic Client Registration endpoint for Claude Custom Connectors"""
    try:
        body = await request.json()

        # Validate Claude's registration request
        if body.get("client_name") != "claudeai":
            raise HTTPException(status_code=400, detail="Unsupported client")

        # Generate unique client credentials for Claude
        import secrets
        client_id = secrets.token_hex(16)

        # Claude expects this exact response format
        return {
            "client_id": client_id,
            "client_name": "claudeai",
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
            "scope": "claudeai",
            "redirect_uris": [
                "https://claude.ai/api/mcp/auth_callback"
            ],
            "client_id_issued_at": int(datetime.now(timezone.utc).timestamp())
        }

    except Exception as e:
        logger.error(f"Client registration error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/oauth/authorize")
async def oauth_authorize(
    response_type: str = "code",
    client_id: str = "test-client",
    redirect_uri: str = "http://localhost:3000/callback",
    state: str = None,
    scope: str = None,
    code_challenge: str = None,
    code_challenge_method: str = None
):
    """OAuth Authorization endpoint - renders user consent form"""
    try:
        # In production, validate client_id exists from registration
        # For demo, we'll accept any client_id that looks like a hex string

        # PKCE is required for real OAuth but optional for testing
        if code_challenge and code_challenge_method != "S256":
            raise HTTPException(status_code=400, detail="PKCE method must be S256")

        # For testing without PKCE, generate a dummy challenge
        if not code_challenge:
            code_challenge = "test_challenge"
            code_challenge_method = "S256"

        # Return HTML consent form
        html_form = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Monarch Money MCP Authorization</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 400px; margin: 50px auto; padding: 20px; }}
                .form-group {{ margin: 15px 0; }}
                label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
                input {{ width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; }}
                button {{ width: 100%; padding: 10px; background: #007cba; color: white; border: none; border-radius: 4px; font-size: 16px; }}
                .info {{ background: #f0f8ff; padding: 10px; border-radius: 4px; margin-bottom: 20px; }}
            </style>
        </head>
        <body>
            <h2>Authorize Claude MCP Access</h2>
            <div class="info">
                <p><strong>Claude</strong> wants to access your Monarch Money data.</p>
                <p>This will allow Claude to read your accounts, transactions, and budgets.</p>
            </div>
            <form method="POST" action="/oauth/authorize">
                <input type="hidden" name="client_id" value="{client_id}">
                <input type="hidden" name="code_challenge" value="{code_challenge}">
                <input type="hidden" name="code_challenge_method" value="{code_challenge_method}">
                <input type="hidden" name="redirect_uri" value="{redirect_uri}">
                <input type="hidden" name="response_type" value="{response_type}">
                <input type="hidden" name="scope" value="{scope or 'claudeai'}">
                {f'<input type="hidden" name="state" value="{state}">' if state else ''}

                <div class="form-group">
                    <label>This is a demo - click Authorize to continue:</label>
                </div>

                <button type="submit" name="action" value="authorize">Authorize Access</button>
            </form>
        </body>
        </html>
        """

        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=html_form)

    except Exception as e:
        logger.error(f"Authorization error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/oauth/authorize")
async def oauth_authorize_post(request: Request):
    """Process authorization form submission"""
    try:
        form_data = await request.form()

        action = form_data.get("action")
        if action != "authorize":
            raise HTTPException(status_code=400, detail="Authorization denied")

        client_id = form_data["client_id"]
        code_challenge = form_data["code_challenge"]
        redirect_uri = form_data["redirect_uri"]
        state = form_data.get("state")

        # Generate secure authorization code
        import secrets
        auth_code = secrets.token_hex(32)

        # Store authorization code with PKCE challenge for token exchange
        # In production, store this securely with expiration
        auth_storage[auth_code] = {
            "client_id": client_id,
            "code_challenge": code_challenge,
            "redirect_uri": redirect_uri,
            "expires_at": datetime.now(timezone.utc).timestamp() + 600,  # 10 minutes
            "user_id": "demo_user"  # In real app, get from authentication
        }

        # Redirect back to Claude
        callback_url = f"{redirect_uri}?code={auth_code}"
        if state:
            callback_url += f"&state={state}"

        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=callback_url, status_code=302)

    except Exception as e:
        logger.error(f"Authorization processing error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/oauth/token")
async def oauth_token(request: Request):
    """OAuth Token endpoint - handles both authorization_code and refresh_token grants"""
    try:
        form_data = await request.form()
        grant_type = form_data.get("grant_type")

        if grant_type == "authorization_code":
            code = form_data.get("code")
            client_id = form_data.get("client_id")
            code_verifier = form_data.get("code_verifier")
            redirect_uri = form_data.get("redirect_uri")

            # Validate authorization code
            if code not in auth_storage:
                raise HTTPException(status_code=400, detail="Invalid authorization code")

            auth_data = auth_storage[code]

            # Check expiration
            if datetime.now(timezone.utc).timestamp() > auth_data["expires_at"]:
                del auth_storage[code]
                raise HTTPException(status_code=400, detail="Authorization code expired")

            # Validate PKCE (skip validation for test challenge)
            if auth_data["code_challenge"] != "test_challenge":
                import hashlib
                import base64
                expected_challenge = base64.urlsafe_b64encode(
                    hashlib.sha256(code_verifier.encode()).digest()
                ).decode().rstrip('=')

                if expected_challenge != auth_data["code_challenge"]:
                    raise HTTPException(status_code=400, detail="Invalid code verifier")

            # Validate client and redirect URI
            if client_id != auth_data["client_id"] or redirect_uri != auth_data["redirect_uri"]:
                raise HTTPException(status_code=400, detail="Client or redirect URI mismatch")

            # Clean up used code
            del auth_storage[code]

            # Generate tokens
            import secrets
            access_token = f"mcp_access_{secrets.token_hex(32)}"
            refresh_token = f"mcp_refresh_{secrets.token_hex(32)}"

            # Store tokens for validation (in production, use secure storage)
            token_storage[access_token] = {
                "user_id": auth_data["user_id"],
                "client_id": client_id,
                "expires_at": datetime.now(timezone.utc).timestamp() + 3600,  # 1 hour
                "scope": "claudeai"
            }

            refresh_storage[refresh_token] = {
                "user_id": auth_data["user_id"],
                "client_id": client_id,
                "expires_at": datetime.now(timezone.utc).timestamp() + 2592000,  # 30 days
            }

            return {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": 3600,
                "refresh_token": refresh_token,
                "scope": "claudeai"
            }

        elif grant_type == "refresh_token":
            refresh_token = form_data.get("refresh_token")
            client_id = form_data.get("client_id")

            if refresh_token not in refresh_storage:
                raise HTTPException(status_code=400, detail="Invalid refresh token")

            refresh_data = refresh_storage[refresh_token]

            if datetime.now(timezone.utc).timestamp() > refresh_data["expires_at"]:
                del refresh_storage[refresh_token]
                raise HTTPException(status_code=400, detail="Refresh token expired")

            if client_id != refresh_data["client_id"]:
                raise HTTPException(status_code=400, detail="Client ID mismatch")

            # Generate new access token
            import secrets
            access_token = f"mcp_access_{secrets.token_hex(32)}"

            token_storage[access_token] = {
                "user_id": refresh_data["user_id"],
                "client_id": client_id,
                "expires_at": datetime.now(timezone.utc).timestamp() + 3600,
                "scope": "claudeai"
            }

            return {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": "claudeai"
            }

        else:
            raise HTTPException(status_code=400, detail="Unsupported grant type")

    except Exception as e:
        logger.error(f"Token exchange error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# In-memory storage for demo (use secure storage in production)
auth_storage = {}  # authorization codes
token_storage = {}  # access tokens
refresh_storage = {}  # refresh tokens

# MCP Protocol Endpoints
async def get_bearer_token(authorization: str = Header(None)) -> str:
    """Extract and validate bearer token for Claude"""
    if not authorization or not authorization.startswith("Bearer "):
        # Return proper WWW-Authenticate header as per OAuth spec
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": 'Bearer realm="mcp", authorization_uri="/.well-known/oauth-protected-resource"'}
        )

    token = authorization.split(" ", 1)[1]

    # Validate token exists and hasn't expired
    if token not in token_storage:
        raise HTTPException(
            status_code=401,
            detail="Invalid access token",
            headers={"WWW-Authenticate": 'Bearer realm="mcp", authorization_uri="/.well-known/oauth-protected-resource"'}
        )

    token_data = token_storage[token]
    if datetime.now(timezone.utc).timestamp() > token_data["expires_at"]:
        del token_storage[token]
        raise HTTPException(
            status_code=401,
            detail="Access token expired",
            headers={"WWW-Authenticate": 'Bearer realm="mcp", authorization_uri="/.well-known/oauth-protected-resource"'}
        )

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