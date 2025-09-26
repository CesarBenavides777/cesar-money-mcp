"""
OAuth authentication endpoint for Monarch Money MCP
Provides secure login and JWT token generation
"""

import os
import json
import jwt
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
JWT_SECRET = os.getenv("JWT_SECRET")  # You'll set this in Vercel
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")  # Your login username
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH")  # SHA256 hash of your password
TOKEN_EXPIRY_HOURS = int(os.getenv("TOKEN_EXPIRY_HOURS", "24"))
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

def hash_password(password: str) -> str:
    """Hash a password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_token(user_id: str, client_id: Optional[str] = None) -> Dict[str, Any]:
    """Generate JWT access token"""
    if not JWT_SECRET:
        raise ValueError("JWT_SECRET not configured")

    # Token payload
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(hours=TOKEN_EXPIRY_HOURS)

    payload = {
        "sub": user_id,  # Subject (user identifier)
        "iat": now.timestamp(),  # Issued at
        "exp": expiry.timestamp(),  # Expiration
        "jti": secrets.token_urlsafe(16),  # JWT ID (unique identifier)
        "scope": "monarch:read monarch:write",  # Permissions
    }

    if client_id:
        payload["client_id"] = client_id

    # Generate token
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": TOKEN_EXPIRY_HOURS * 3600,
        "expires_at": expiry.isoformat(),
        "scope": payload["scope"]
    }

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode JWT token"""
    if not JWT_SECRET:
        logger.error("JWT_SECRET not configured")
        return None

    try:
        # Decode and verify token
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_exp": True}
        )
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None

def handle_preflight(event: dict) -> dict:
    """Handle CORS preflight requests"""
    origin = event.get("headers", {}).get("origin", "*")
    allowed_origin = origin if origin in ALLOWED_ORIGINS or "*" in ALLOWED_ORIGINS else ALLOWED_ORIGINS[0]

    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": allowed_origin,
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Allow-Credentials": "true" if allowed_origin != "*" else "false",
            "Access-Control-Max-Age": "86400"
        },
        "body": ""
    }

def handle_login(event: dict) -> dict:
    """Handle login requests"""
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Credentials": "true"
    }

    # Parse request body
    try:
        body = json.loads(event.get("body", "{}"))
    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "headers": headers,
            "body": json.dumps({
                "error": "invalid_request",
                "error_description": "Invalid JSON in request body"
            })
        }

    # Get credentials
    username = body.get("username")
    password = body.get("password")
    client_id = body.get("client_id")  # Optional: identify the requesting service

    if not username or not password:
        return {
            "statusCode": 400,
            "headers": headers,
            "body": json.dumps({
                "error": "invalid_request",
                "error_description": "Username and password required"
            })
        }

    # Verify credentials
    if not ADMIN_PASSWORD_HASH:
        # First time setup - show the hash to set in environment
        password_hash = hash_password(password)
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps({
                "error": "configuration_required",
                "error_description": "Set ADMIN_PASSWORD_HASH in environment variables",
                "your_password_hash": password_hash,
                "instructions": "Add this hash to your Vercel environment variables"
            })
        }

    # Check credentials
    if username != ADMIN_USERNAME or hash_password(password) != ADMIN_PASSWORD_HASH:
        return {
            "statusCode": 401,
            "headers": headers,
            "body": json.dumps({
                "error": "invalid_credentials",
                "error_description": "Invalid username or password"
            })
        }

    # Generate token
    try:
        token_data = generate_token(username, client_id)
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps(token_data)
        }
    except ValueError as e:
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps({
                "error": "server_error",
                "error_description": str(e)
            })
        }

def handle_token_info(event: dict) -> dict:
    """Handle token introspection requests"""
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*"
    }

    # Get token from Authorization header
    auth_header = event.get("headers", {}).get("authorization", "")
    if not auth_header.startswith("Bearer "):
        return {
            "statusCode": 401,
            "headers": headers,
            "body": json.dumps({
                "error": "invalid_request",
                "error_description": "Bearer token required"
            })
        }

    token = auth_header[7:]  # Remove "Bearer " prefix

    # Verify token
    payload = verify_token(token)
    if not payload:
        return {
            "statusCode": 401,
            "headers": headers,
            "body": json.dumps({
                "active": False,
                "error": "invalid_token"
            })
        }

    # Return token info
    return {
        "statusCode": 200,
        "headers": headers,
        "body": json.dumps({
            "active": True,
            "sub": payload.get("sub"),
            "scope": payload.get("scope"),
            "client_id": payload.get("client_id"),
            "exp": payload.get("exp"),
            "iat": payload.get("iat"),
            "jti": payload.get("jti")
        })
    }

def handler(event, context):
    """Main handler for auth endpoints"""
    path = event.get("path", "").strip("/")
    method = event.get("httpMethod", "GET")

    # Handle CORS preflight
    if method == "OPTIONS":
        return handle_preflight(event)

    # Route to appropriate handler
    if path == "api/auth/login" and method == "POST":
        return handle_login(event)
    elif path == "api/auth/token" and method == "GET":
        return handle_token_info(event)
    else:
        return {
            "statusCode": 404,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "error": "not_found",
                "error_description": f"Unknown endpoint: {path}"
            })
        }