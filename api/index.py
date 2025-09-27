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

# Import MonarchMoney for type hints and functionality
try:
    from monarchmoney import MonarchMoney, RequireMFAException
except ImportError:
    # Create placeholder for type hints if not available
    MonarchMoney = None
    RequireMFAException = Exception

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

# Helper functions for Monarch Money integration
async def call_monarch_tool(tool_name: str, arguments: dict, user_email: str) -> str:
    """Call Monarch Money tools with authenticated user credentials"""
    try:
        from monarchmoney import MonarchMoney, RequireMFAException

        # Create authenticated client for this user
        client = MonarchMoney()

        # Note: In production, you'd need to store/retrieve the password securely
        # For now, we'll use environment variables as fallback
        password = os.getenv("MONARCH_PASSWORD")
        mfa_secret = os.getenv("MONARCH_MFA_SECRET")

        if not password:
            return "Error: Authentication credentials not available for this user"

        # Login with user credentials
        login_kwargs = {
            "email": user_email,
            "password": password,
            "save_session": False,
            "use_saved_session": False
        }

        if mfa_secret:
            login_kwargs["mfa_secret_key"] = mfa_secret

        await client.login(**login_kwargs)

        # Call the appropriate tool
        if tool_name == "get_accounts":
            return await _get_accounts(client)
        elif tool_name == "get_transactions":
            return await _get_transactions(client, **arguments)
        elif tool_name == "get_budgets":
            return await _get_budgets(client)
        elif tool_name == "get_spending_plan":
            return await _get_spending_plan(client, **arguments)
        elif tool_name == "get_account_history":
            return await _get_account_history(client, **arguments)
        else:
            return f"Unknown tool: {tool_name}"

    except Exception as e:
        logger.error(f"Error calling Monarch tool {tool_name}: {e}")
        return f"Error: {str(e)}"

# Monarch Money tool implementations with ultra-safe string handling
def safe_str(value, default="Unknown"):
    """Ultra-safe string conversion that handles None, empty, and complex objects"""
    try:
        if value is None:
            return str(default)
        if isinstance(value, str):
            return value if value.strip() else str(default)
        if isinstance(value, (int, float)):
            return str(value)
        result = str(value)
        return result if result.strip() else str(default)
    except Exception:
        return str(default)

def safe_dict_get(obj, key, default="Unknown"):
    """Safely get a value from a dictionary-like object"""
    try:
        if obj is None or not isinstance(obj, dict):
            return str(default)
        value = obj.get(key)
        return safe_str(value, default)
    except Exception:
        return str(default)

async def _get_accounts(client) -> str:
    """Get all Monarch Money accounts with balances and details"""
    try:
        result = await client.get_accounts()
        accounts = result.get('accounts', [])

        if not accounts:
            return "No accounts found."

        account_summary = f"Found {len(accounts)} accounts:\\n\\n"

        for account in accounts:
            name_str = safe_str(account.get('displayName'), 'Unknown Account')
            balance = account.get('currentBalance') if account.get('currentBalance') is not None else 0
            account_type = safe_dict_get(account.get('type'), 'display', 'Unknown')
            institution = safe_dict_get(account.get('institution'), 'name', 'Unknown')
            account_id = safe_str(account.get('id'), 'N/A')

            account_summary += f"📊 **{name_str}**\\n"
            account_summary += f"   Balance: ${balance:,.2f}\\n"
            account_summary += f"   Type: {account_type}\\n"
            account_summary += f"   Institution: {institution}\\n"
            account_summary += f"   ID: {account_id}\\n\\n"

        return account_summary

    except Exception as e:
        logger.error(f"Error in _get_accounts: {e}")
        return f"Error fetching accounts: {str(e)}"

async def _get_transactions(client, start_date: str = None, end_date: str = None, limit: int = 100, account_id: str = None) -> str:
    """Get Monarch Money transactions with optional filtering"""
    try:
        kwargs = {"limit": min(max(1, limit), 1000)}

        if start_date:
            kwargs["start_date"] = start_date
        if end_date:
            kwargs["end_date"] = end_date
        if account_id:
            kwargs["account_id"] = account_id

        result = await client.get_transactions(**kwargs)
        transactions = result.get('allTransactions', {}).get('results', [])

        if not transactions:
            return "No transactions found for the specified criteria."

        summary = f"Found {len(transactions)} transactions"
        if start_date:
            summary += f" from {safe_str(start_date, 'Unknown')}"
        if end_date:
            summary += f" to {safe_str(end_date, 'Unknown')}"
        summary += f" (showing up to {limit}):\\n\\n"

        for tx in transactions[:20]:
            date_str = safe_str(tx.get('date'), 'Unknown')
            merchant = safe_dict_get(tx.get('merchant'), 'name', 'Unknown Merchant')
            amount = tx.get('amount') if tx.get('amount') is not None else 0
            category = safe_dict_get(tx.get('category'), 'name', 'Uncategorized')
            account_name = safe_dict_get(tx.get('account'), 'displayName', 'Unknown Account')

            summary += f"💳 **{date_str}** - {merchant}\\n"
            summary += f"   Amount: ${amount:,.2f}\\n"
            summary += f"   Category: {category}\\n"
            summary += f"   Account: {account_name}\\n\\n"

        if len(transactions) > 20:
            summary += f"... and {len(transactions) - 20} more transactions\\n"

        return summary

    except Exception as e:
        logger.error(f"Error in _get_transactions: {e}")
        return f"Error fetching transactions: {str(e)}"

async def _get_budgets(client) -> str:
    """Get Monarch Money budget information and categories"""
    try:
        result = await client.get_budgets()

        if not result:
            return "No budget information available."

        budget_text = "📊 **Budget Information**\\n\\n"

        if isinstance(result, list):
            for budget in result:
                name = safe_str(budget.get('name'), 'Unnamed Budget')
                budget_text += f"Budget: {name}\\n"
        else:
            budget_text += f"Budget data: {safe_str(result, 'No data')}\\n"

        return budget_text

    except Exception as e:
        logger.error(f"Error in _get_budgets: {e}")
        return f"Error fetching budgets: {str(e)}"

async def _get_spending_plan(client, month: str = None) -> str:
    """Get spending plan for a specific month"""
    try:
        from datetime import datetime, date

        if month:
            try:
                year, month_num = map(int, month.split('-'))
                start_date = date(year, month_num, 1)
                if month_num == 12:
                    end_date = date(year + 1, 1, 1)
                else:
                    end_date = date(year, month_num + 1, 1)
            except ValueError:
                return "Invalid month format. Use YYYY-MM format."
        else:
            now = datetime.now()
            start_date = date(now.year, now.month, 1)
            if now.month == 12:
                end_date = date(now.year + 1, 1, 1)
            else:
                end_date = date(now.year, now.month + 1, 1)

        result = await client.get_spending_plan(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat()
        )

        plan_text = f"📈 **Spending Plan for {start_date.strftime('%Y-%m')}**\\n\\n"
        plan_text += f"Plan data: {str(result)}\\n"

        return plan_text

    except Exception as e:
        logger.error(f"Error in _get_spending_plan: {e}")
        return f"Error fetching spending plan: {str(e)}"

async def _get_account_history(client, account_id: str, start_date: str = None, end_date: str = None) -> str:
    """Get balance history for a specific account"""
    try:
        from datetime import datetime

        parsed_start = None
        parsed_end = None

        if start_date:
            try:
                parsed_start = datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError:
                return "Invalid start_date format. Use YYYY-MM-DD format."

        if end_date:
            try:
                parsed_end = datetime.strptime(end_date, "%Y-%m-%d").date()
            except ValueError:
                return "Invalid end_date format. Use YYYY-MM-DD format."

        result = await client.get_account_history(
            account_id=account_id,
            start_date=parsed_start.isoformat() if parsed_start else None,
            end_date=parsed_end.isoformat() if parsed_end else None
        )

        if not result:
            return f"No history found for account {account_id}"

        history_text = f"📊 **Account History for {account_id}**\\n\\n"
        history_text += f"History data: {str(result)}\\n"

        return history_text

    except Exception as e:
        logger.error(f"Error in _get_account_history: {e}")
        return f"Error fetching account history: {str(e)}"

# Dynamic Client Registration (RFC 7591) - Required for Claude Custom Connectors
@app.post("/oauth/register")
async def oauth_register(request: Request):
    """Dynamic Client Registration endpoint for Claude Custom Connectors"""
    try:
        body = await request.json()

        # Accept any client registration for Claude compatibility
        client_name = body.get("client_name", "claude-mcp-client")

        # Generate unique client credentials for Claude
        import secrets
        client_id = secrets.token_hex(16)

        # Return registration response compatible with Claude
        return {
            "client_id": client_id,
            "client_name": client_name,
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
            "scope": body.get("scope", "claudeai"),
            "redirect_uris": body.get("redirect_uris", [
                "https://claude.ai/api/mcp/auth_callback"
            ]),
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

        # Return HTML login form for real Monarch Money authentication
        html_form = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Monarch Money Login - Claude MCP</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 400px; margin: 50px auto; padding: 30px; background: #f5f5f5; }}
                .container {{ background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); }}
                .logo {{ text-align: center; margin-bottom: 30px; }}
                .logo h1 {{ color: #2c5aa0; margin: 0; font-size: 24px; }}
                .form-group {{ margin: 20px 0; }}
                label {{ display: block; margin-bottom: 8px; font-weight: 600; color: #333; }}
                input[type="email"], input[type="password"], input[type="text"] {{ width: 100%; padding: 12px; border: 2px solid #e1e5e9; border-radius: 8px; font-size: 16px; transition: border-color 0.2s; }}
                input[type="email"]:focus, input[type="password"]:focus, input[type="text"]:focus {{ outline: none; border-color: #2c5aa0; }}
                button {{ width: 100%; padding: 12px; background: #2c5aa0; color: white; border: none; border-radius: 8px; font-size: 16px; font-weight: 600; cursor: pointer; transition: background 0.2s; }}
                button:hover {{ background: #1e3f73; }}
                .info {{ background: #e8f4fd; padding: 15px; border-radius: 8px; margin-bottom: 25px; border-left: 4px solid #2c5aa0; }}
                .mfa-info {{ background: #fff3cd; padding: 10px; border-radius: 6px; margin-top: 10px; font-size: 14px; color: #856404; }}
                .checkbox-group {{ display: flex; align-items: center; margin: 15px 0; }}
                .checkbox-group input {{ width: auto; margin-right: 8px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="logo">
                    <h1>👑 Monarch Money</h1>
                    <p style="color: #666; margin: 5px 0 0 0;">Connect to Claude</p>
                </div>

                <div class="info">
                    <p><strong>🤖 Claude</strong> wants to access your Monarch Money data.</p>
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
                        <label for="email">Email Address</label>
                        <input type="email" id="email" name="email" required placeholder="your.email@example.com">
                    </div>

                    <div class="form-group">
                        <label for="password">Password</label>
                        <input type="password" id="password" name="password" required placeholder="Your Monarch Money password">
                    </div>

                    <div class="form-group">
                        <label for="mfa_secret">MFA Secret Key (if enabled)</label>
                        <input type="text" id="mfa_secret" name="mfa_secret" placeholder="Your base32 MFA secret key">
                        <div class="mfa-info">
                            💡 Leave blank if you don't have MFA enabled. Enter your MFA secret key (base32 string) if you do.
                        </div>
                    </div>

                    <button type="submit" name="action" value="login">🔒 Login & Authorize Claude</button>
                </form>
            </div>
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
        if action != "login":
            raise HTTPException(status_code=400, detail="Authorization denied")

        # Get form data
        client_id = form_data["client_id"]
        code_challenge = form_data["code_challenge"]
        redirect_uri = form_data["redirect_uri"]
        state = form_data.get("state")

        # Get Monarch Money credentials
        email = form_data.get("email")
        password = form_data.get("password")
        mfa_secret = form_data.get("mfa_secret")

        if not email or not password:
            raise HTTPException(status_code=400, detail="Email and password are required")

        # Authenticate with Monarch Money
        try:
            from monarchmoney import MonarchMoney, RequireMFAException

            client = MonarchMoney()

            # Prepare login kwargs
            login_kwargs = {
                "email": email,
                "password": password,
                "save_session": False,
                "use_saved_session": False
            }

            # Add MFA secret key if provided
            if mfa_secret and mfa_secret.strip():
                login_kwargs["mfa_secret_key"] = mfa_secret.strip()

            # Attempt login
            await client.login(**login_kwargs)
            logger.info(f"Successfully authenticated user: {email[:3]}...{email[-10:]}")

            # Create user ID from email (hashed for privacy)
            import hashlib
            user_id = hashlib.sha256(email.encode()).hexdigest()[:16]

        except RequireMFAException:
            # Return form with MFA error
            error_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>MFA Required - Monarch Money</title>
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 400px; margin: 50px auto; padding: 30px; background: #f5f5f5; }}
                    .container {{ background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); }}
                    .error {{ background: #fee; padding: 15px; border-radius: 8px; margin-bottom: 25px; border-left: 4px solid #e74c3c; color: #c0392b; }}
                    .back-link {{ text-align: center; margin-top: 20px; }}
                    .back-link a {{ color: #2c5aa0; text-decoration: none; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="error">
                        <p><strong>🔐 MFA Required</strong></p>
                        <p>Your account requires MFA authentication. Please go back and enter your MFA secret key (base32 string).</p>
                    </div>
                    <div class="back-link">
                        <a href="javascript:history.back()">← Go Back</a>
                    </div>
                </div>
            </body>
            </html>
            """
            from fastapi.responses import HTMLResponse
            return HTMLResponse(content=error_html, status_code=400)

        except Exception as e:
            logger.error(f"Monarch Money authentication failed: {e}")
            # Return form with error
            error_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Login Failed - Monarch Money</title>
                <style>
                    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 400px; margin: 50px auto; padding: 30px; background: #f5f5f5; }}
                    .container {{ background: white; padding: 30px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); }}
                    .error {{ background: #fee; padding: 15px; border-radius: 8px; margin-bottom: 25px; border-left: 4px solid #e74c3c; color: #c0392b; }}
                    .back-link {{ text-align: center; margin-top: 20px; }}
                    .back-link a {{ color: #2c5aa0; text-decoration: none; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="error">
                        <p><strong>❌ Login Failed</strong></p>
                        <p>Invalid email, password, or MFA code. Please check your credentials and try again.</p>
                        <p><small>Error: {str(e)[:100]}</small></p>
                    </div>
                    <div class="back-link">
                        <a href="javascript:history.back()">← Try Again</a>
                    </div>
                </div>
            </body>
            </html>
            """
            from fastapi.responses import HTMLResponse
            return HTMLResponse(content=error_html, status_code=400)

        # Generate secure authorization code
        import secrets
        auth_code = secrets.token_hex(32)

        # Store authorization code with PKCE challenge and authenticated user info
        auth_storage[auth_code] = {
            "client_id": client_id,
            "code_challenge": code_challenge,
            "redirect_uri": redirect_uri,
            "expires_at": datetime.now(timezone.utc).timestamp() + 600,  # 10 minutes
            "user_id": user_id,
            "email": email,  # Store for token validation
            "authenticated": True
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
                "scope": "claudeai",
                "email": auth_data.get("email"),  # Store for MCP tool authentication
                "authenticated": auth_data.get("authenticated", False)
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
async def mcp_rpc(request: Request, authorization: str = Header(None)):
    """MCP JSON-RPC endpoint"""
    try:
        body = await request.json()

        method = body.get("method")
        params = body.get("params", {})
        request_id = body.get("id")

        logger.info(f"MCP RPC call: {method}")

        # Allow initialize and tools/list without authentication for discovery
        requires_auth = method not in ["initialize", "tools/list"]

        if requires_auth:
            # Validate token for methods that require authentication
            if not authorization or not authorization.startswith("Bearer "):
                raise HTTPException(
                    status_code=401,
                    detail="Unauthorized",
                    headers={"WWW-Authenticate": 'Bearer realm="mcp"'}
                )
            token = authorization.split(" ", 1)[1]
            if token not in token_storage:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid access token",
                    headers={"WWW-Authenticate": 'Bearer realm="mcp"'}
                )
            token_data = token_storage[token]
            if datetime.now(timezone.utc).timestamp() > token_data["expires_at"]:
                del token_storage[token]
                raise HTTPException(
                    status_code=401,
                    detail="Access token expired",
                    headers={"WWW-Authenticate": 'Bearer realm="mcp"'}
                )
        else:
            token = None  # No token needed for discovery methods

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
                        },
                        {
                            "name": "get_spending_plan",
                            "description": "Get spending plan for a specific month",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "month": {"type": "string", "description": "Month in YYYY-MM format (defaults to current month)"}
                                },
                                "required": []
                            }
                        },
                        {
                            "name": "get_account_history",
                            "description": "Get balance history for a specific account",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "account_id": {"type": "string", "description": "Account ID to get history for"},
                                    "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format"},
                                    "end_date": {"type": "string", "description": "End date in YYYY-MM-DD format"}
                                },
                                "required": ["account_id"]
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

            # This method requires authentication, so token should be available
            if not token:
                raise HTTPException(status_code=401, detail="Authentication required for tool calls")

            # Get user credentials from token
            token_data = token_storage.get(token)
            if not token_data or not token_data.get("authenticated"):
                raise HTTPException(status_code=401, detail="User not authenticated with Monarch Money")

            user_email = token_data.get("email")
            if not user_email:
                raise HTTPException(status_code=401, detail="User credentials not found")

            # Call tools with authenticated user's credentials
            result_text = await call_monarch_tool(tool_name, arguments, user_email)

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