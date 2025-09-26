"""
Vercel serverless function for Monarch Money MCP
Provides HTTP API endpoints with API key authentication
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime

# Vercel uses Python 3.9+ by default, ensure compatibility
import sys
if sys.version_info < (3, 9):
    raise RuntimeError("Python 3.9+ required")

# Import monarchmoney library
from monarchmoney import MonarchMoney, RequireMFAException

# Import auth module for token verification
try:
    from .auth import verify_token
except ImportError:
    from auth import verify_token

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables (set in Vercel dashboard)
API_KEY = os.getenv("API_KEY")
MONARCH_EMAIL = os.getenv("MONARCH_EMAIL")
MONARCH_PASSWORD = os.getenv("MONARCH_PASSWORD")
MONARCH_MFA_SECRET = os.getenv("MONARCH_MFA_SECRET")
JWT_SECRET = os.getenv("JWT_SECRET")  # For OAuth token verification

class AuthError(Exception):
    """Authentication error"""
    pass

def verify_auth(headers: dict) -> tuple[bool, Optional[str]]:
    """Verify authentication via API key or OAuth token

    Returns:
        (is_authenticated, auth_method)
    """
    # Check for OAuth Bearer token first
    auth_header = headers.get("authorization") or headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]  # Remove "Bearer " prefix
        token_payload = verify_token(token)
        if token_payload:
            logger.info(f"OAuth token authenticated for user: {token_payload.get('sub')}")
            return True, "oauth"

    # Check for API key
    if API_KEY:
        provided_key = headers.get("x-api-key") or headers.get("X-API-Key")
        if provided_key:
            import hmac
            if hmac.compare_digest(provided_key, API_KEY):
                logger.info("API key authenticated")
                return True, "api_key"

    logger.warning("No valid authentication provided")
    return False, None

async def get_monarch_client() -> MonarchMoney:
    """Create and authenticate Monarch Money client"""
    if not MONARCH_EMAIL or not MONARCH_PASSWORD:
        raise ValueError("Monarch credentials not configured")

    client = MonarchMoney()

    try:
        await client.login(
            email=MONARCH_EMAIL,
            password=MONARCH_PASSWORD,
            mfa_secret_key=MONARCH_MFA_SECRET,
            save_session=False,
            use_saved_session=False
        )
        return client
    except RequireMFAException:
        raise AuthError("MFA required but not configured")
    except Exception as e:
        logger.error(f"Monarch login failed: {e}")
        raise AuthError(f"Authentication failed: {str(e)}")

async def handle_get_accounts() -> Dict[str, Any]:
    """Handle get_accounts request"""
    try:
        client = await get_monarch_client()
        result = await client.get_accounts()
        accounts = result.get('accounts', [])

        return {
            "success": True,
            "data": accounts,
            "count": len(accounts)
        }
    except AuthError as e:
        return {
            "success": False,
            "error": str(e),
            "code": "AUTH_ERROR"
        }
    except Exception as e:
        logger.error(f"Error fetching accounts: {e}")
        return {
            "success": False,
            "error": "Failed to fetch accounts",
            "code": "FETCH_ERROR"
        }

async def handle_get_transactions(params: dict) -> Dict[str, Any]:
    """Handle get_transactions request"""
    try:
        client = await get_monarch_client()

        # Extract parameters
        start_date = params.get("start_date")
        end_date = params.get("end_date")
        limit = min(int(params.get("limit", 100)), 1000)  # Cap at 1000

        # Parse dates if provided
        if start_date:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        if end_date:
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

        # Fetch transactions
        result = await client.get_transactions(
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )

        transactions = result.get('allTransactions', {}).get('results', [])

        return {
            "success": True,
            "data": transactions,
            "count": len(transactions),
            "parameters": {
                "start_date": str(start_date) if start_date else None,
                "end_date": str(end_date) if end_date else None,
                "limit": limit
            }
        }
    except AuthError as e:
        return {
            "success": False,
            "error": str(e),
            "code": "AUTH_ERROR"
        }
    except ValueError as e:
        return {
            "success": False,
            "error": f"Invalid parameters: {str(e)}",
            "code": "INVALID_PARAMS"
        }
    except Exception as e:
        logger.error(f"Error fetching transactions: {e}")
        return {
            "success": False,
            "error": "Failed to fetch transactions",
            "code": "FETCH_ERROR"
        }

async def handle_get_budgets() -> Dict[str, Any]:
    """Handle get_budgets request"""
    try:
        client = await get_monarch_client()
        result = await client.get_budgets()

        return {
            "success": True,
            "data": result,
            "count": len(result) if isinstance(result, list) else 1
        }
    except AuthError as e:
        return {
            "success": False,
            "error": str(e),
            "code": "AUTH_ERROR"
        }
    except Exception as e:
        logger.error(f"Error fetching budgets: {e}")
        return {
            "success": False,
            "error": "Failed to fetch budgets",
            "code": "FETCH_ERROR"
        }

async def handle_get_spending_plan() -> Dict[str, Any]:
    """Handle get_spending_plan request"""
    try:
        client = await get_monarch_client()

        # Get current month's spending plan
        now = datetime.now()
        result = await client.get_spending_plan(
            start_date=datetime(now.year, now.month, 1).date(),
            end_date=datetime(now.year, now.month + 1 if now.month < 12 else 1, 1).date()
        )

        return {
            "success": True,
            "data": result,
            "month": f"{now.year}-{now.month:02d}"
        }
    except AuthError as e:
        return {
            "success": False,
            "error": str(e),
            "code": "AUTH_ERROR"
        }
    except Exception as e:
        logger.error(f"Error fetching spending plan: {e}")
        return {
            "success": False,
            "error": "Failed to fetch spending plan",
            "code": "FETCH_ERROR"
        }

async def handle_request(event: dict) -> dict:
    """Main request handler for Vercel"""
    # CORS headers
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",  # Configure this for your domain in production
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
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
    is_authenticated, auth_method = verify_auth(request_headers)

    if not is_authenticated:
        return {
            "statusCode": 401,
            "headers": headers,
            "body": json.dumps({
                "success": False,
                "error": "Authentication required. Provide either Bearer token or X-API-Key",
                "code": "UNAUTHORIZED",
                "auth_url": "/api/auth/login"
            })
        }

    # Parse request
    path = event.get("path", "").strip("/")
    method = event.get("httpMethod", "GET")

    # Parse query parameters or body
    params = {}
    if method == "GET":
        params = event.get("queryStringParameters", {}) or {}
    elif method == "POST":
        body = event.get("body", "")
        if body:
            try:
                params = json.loads(body)
            except json.JSONDecodeError:
                return {
                    "statusCode": 400,
                    "headers": headers,
                    "body": json.dumps({
                        "success": False,
                        "error": "Invalid JSON in request body",
                        "code": "INVALID_JSON"
                    })
                }

    # Route to appropriate handler
    try:
        if path == "api" or path == "":
            # Return available endpoints
            result = {
                "success": True,
                "service": "Monarch Money MCP API",
                "version": "1.0.0",
                "endpoints": [
                    "/api/accounts",
                    "/api/transactions",
                    "/api/budgets",
                    "/api/spending-plan"
                ]
            }
        elif path == "api/accounts":
            result = await handle_get_accounts()
        elif path == "api/transactions":
            result = await handle_get_transactions(params)
        elif path == "api/budgets":
            result = await handle_get_budgets()
        elif path == "api/spending-plan":
            result = await handle_get_spending_plan()
        else:
            return {
                "statusCode": 404,
                "headers": headers,
                "body": json.dumps({
                    "success": False,
                    "error": f"Unknown endpoint: {path}",
                    "code": "NOT_FOUND"
                })
            }

        # Return success response
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps(result)
        }

    except Exception as e:
        logger.error(f"Unhandled error: {e}")
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps({
                "success": False,
                "error": "Internal server error",
                "code": "INTERNAL_ERROR"
            })
        }

# Vercel entry point
def handler(event, context):
    """Vercel Python runtime entry point"""
    import asyncio

    # Run async handler
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        return loop.run_until_complete(handle_request(event))
    finally:
        loop.close()