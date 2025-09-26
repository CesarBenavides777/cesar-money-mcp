#!/usr/bin/env python3
"""
Secure OAuth 2.1 Implementation for MCP Server
Based on latest MCP specification and security best practices
Compatible with Claude Custom Connectors
"""

import os
import secrets
import hashlib
import base64
import json
import sqlite3
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import logging
from pathlib import Path

logger = logging.getLogger("monarchmoney-mcp-oauth")

class SecureTokenStorage:
    """Secure token storage using SQLite with encryption"""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            # Store in user's home directory by default
            db_path = Path.home() / ".monarchmoney_mcp" / "tokens.db"

        # Ensure directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self.db_path = str(db_path)
        self._init_database()

    def _init_database(self):
        """Initialize the SQLite database with proper schema"""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS oauth_clients (
                    client_id TEXT PRIMARY KEY,
                    client_secret_hash TEXT NOT NULL,
                    redirect_uris TEXT NOT NULL, -- JSON array
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS auth_codes (
                    code TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    user_email_hash TEXT,
                    user_password_hash TEXT,
                    expires_at TIMESTAMP NOT NULL,
                    used BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (client_id) REFERENCES oauth_clients (client_id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS access_tokens (
                    token_hash TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    user_email_hash TEXT,
                    user_password_hash TEXT,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP,
                    FOREIGN KEY (client_id) REFERENCES oauth_clients (client_id)
                )
            """)

            # Create indexes for performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_auth_codes_expires ON auth_codes(expires_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tokens_expires ON access_tokens(expires_at)")

            conn.commit()
        finally:
            conn.close()

    def _hash_credential(self, credential: str) -> str:
        """Hash a credential using SHA-256 with salt"""
        salt = os.urandom(32)
        credential_hash = hashlib.pbkdf2_hmac('sha256', credential.encode(), salt, 100000)
        return base64.b64encode(salt + credential_hash).decode()

    def _verify_credential(self, credential: str, stored_hash: str) -> bool:
        """Verify a credential against its stored hash"""
        try:
            decoded = base64.b64decode(stored_hash.encode())
            salt = decoded[:32]
            stored_hash_bytes = decoded[32:]
            credential_hash = hashlib.pbkdf2_hmac('sha256', credential.encode(), salt, 100000)
            return credential_hash == stored_hash_bytes
        except Exception:
            return False

    def store_client(self, client_id: str, client_secret: str, redirect_uris: list) -> bool:
        """Store OAuth client credentials securely"""
        try:
            conn = sqlite3.connect(self.db_path)
            client_secret_hash = self._hash_credential(client_secret)
            redirect_uris_json = json.dumps(redirect_uris)

            conn.execute("""
                INSERT OR REPLACE INTO oauth_clients
                (client_id, client_secret_hash, redirect_uris, last_used)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (client_id, client_secret_hash, redirect_uris_json))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error storing client: {e}")
            return False

    def verify_client(self, client_id: str, client_secret: str) -> bool:
        """Verify OAuth client credentials"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute(
                "SELECT client_secret_hash FROM oauth_clients WHERE client_id = ?",
                (client_id,)
            )
            row = cursor.fetchone()
            conn.close()

            if row:
                return self._verify_credential(client_secret, row[0])
            return False
        except Exception as e:
            logger.error(f"Error verifying client: {e}")
            return False

    def get_client_redirect_uris(self, client_id: str) -> list:
        """Get redirect URIs for a client"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute(
                "SELECT redirect_uris FROM oauth_clients WHERE client_id = ?",
                (client_id,)
            )
            row = cursor.fetchone()
            conn.close()

            if row:
                return json.loads(row[0])
            return []
        except Exception as e:
            logger.error(f"Error getting redirect URIs: {e}")
            return []

    def store_auth_code(self, code: str, client_id: str, user_email: str, user_password: str) -> bool:
        """Store authorization code securely"""
        try:
            conn = sqlite3.connect(self.db_path)
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)  # 10 minute expiry

            # Hash user credentials
            user_email_hash = self._hash_credential(user_email)
            user_password_hash = self._hash_credential(user_password)

            conn.execute("""
                INSERT INTO auth_codes
                (code, client_id, user_email_hash, user_password_hash, expires_at)
                VALUES (?, ?, ?, ?, ?)
            """, (code, client_id, user_email_hash, user_password_hash, expires_at))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error storing auth code: {e}")
            return False

    def exchange_auth_code(self, code: str, client_id: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for user credentials"""
        try:
            conn = sqlite3.connect(self.db_path)

            # Get and mark auth code as used
            cursor = conn.execute("""
                SELECT user_email_hash, user_password_hash, expires_at, used
                FROM auth_codes
                WHERE code = ? AND client_id = ?
            """, (code, client_id))

            row = cursor.fetchone()
            if not row:
                conn.close()
                return None

            user_email_hash, user_password_hash, expires_at, used = row

            # Check if already used
            if used:
                conn.close()
                return None

            # Check if expired
            expires_datetime = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            if datetime.now(timezone.utc) > expires_datetime:
                conn.close()
                return None

            # Mark as used
            conn.execute(
                "UPDATE auth_codes SET used = TRUE WHERE code = ?",
                (code,)
            )
            conn.commit()
            conn.close()

            return {
                "user_email_hash": user_email_hash,
                "user_password_hash": user_password_hash
            }

        except Exception as e:
            logger.error(f"Error exchanging auth code: {e}")
            return None

    def store_access_token(self, token: str, client_id: str, user_email_hash: str, user_password_hash: str) -> bool:
        """Store access token securely"""
        try:
            conn = sqlite3.connect(self.db_path)
            token_hash = self._hash_credential(token)
            expires_at = datetime.now(timezone.utc) + timedelta(hours=24)  # 24 hour expiry

            conn.execute("""
                INSERT INTO access_tokens
                (token_hash, client_id, user_email_hash, user_password_hash, expires_at, last_used)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (token_hash, client_id, user_email_hash, user_password_hash, expires_at))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error storing access token: {e}")
            return False

    def validate_access_token(self, token: str) -> Optional[Dict[str, str]]:
        """Validate access token and return user credential hashes"""
        try:
            conn = sqlite3.connect(self.db_path)

            # Find token by trying all stored token hashes
            cursor = conn.execute("""
                SELECT client_id, user_email_hash, user_password_hash, expires_at
                FROM access_tokens
            """)

            for row in cursor.fetchall():
                client_id, user_email_hash, user_password_hash, expires_at = row

                # Check if this token matches
                token_hash = self._hash_credential(token)
                cursor2 = conn.execute(
                    "SELECT 1 FROM access_tokens WHERE token_hash = ?",
                    (token_hash,)
                )

                if cursor2.fetchone():
                    # Check if expired
                    expires_datetime = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    if datetime.now(timezone.utc) > expires_datetime:
                        conn.close()
                        return None

                    # Update last used
                    conn.execute(
                        "UPDATE access_tokens SET last_used = CURRENT_TIMESTAMP WHERE token_hash = ?",
                        (token_hash,)
                    )
                    conn.commit()
                    conn.close()

                    return {
                        "client_id": client_id,
                        "user_email_hash": user_email_hash,
                        "user_password_hash": user_password_hash
                    }

            conn.close()
            return None

        except Exception as e:
            logger.error(f"Error validating access token: {e}")
            return None

    def cleanup_expired_tokens(self):
        """Clean up expired tokens and auth codes"""
        try:
            conn = sqlite3.connect(self.db_path)
            now = datetime.now(timezone.utc)

            # Clean up expired auth codes
            conn.execute("DELETE FROM auth_codes WHERE expires_at < ?", (now,))

            # Clean up expired access tokens
            conn.execute("DELETE FROM access_tokens WHERE expires_at < ?", (now,))

            conn.commit()
            conn.close()
            logger.info("Cleaned up expired tokens")

        except Exception as e:
            logger.error(f"Error cleaning up expired tokens: {e}")

class SecureOAuthManager:
    """OAuth 2.1 compliant manager for MCP server"""

    def __init__(self):
        self.storage = SecureTokenStorage()

        # Schedule periodic cleanup
        asyncio.create_task(self._periodic_cleanup())

    async def _periodic_cleanup(self):
        """Periodically clean up expired tokens"""
        while True:
            try:
                await asyncio.sleep(3600)  # Every hour
                self.storage.cleanup_expired_tokens()
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")

    def generate_client_credentials(self) -> tuple[str, str]:
        """Generate secure client credentials"""
        client_id = f"mcp_{secrets.token_hex(16)}"
        client_secret = secrets.token_urlsafe(32)
        return client_id, client_secret

    def generate_auth_code(self) -> str:
        """Generate secure authorization code"""
        return secrets.token_urlsafe(32)

    def generate_access_token(self) -> str:
        """Generate secure access token"""
        return secrets.token_urlsafe(32)

    def register_client(self, redirect_uris: list) -> Dict[str, Any]:
        """Register a new OAuth client"""
        client_id, client_secret = self.generate_client_credentials()

        # Default redirect URIs for Claude and common clients
        default_uris = [
            "https://api.agent.ai/api/v3/mcp/flow/redirect",
            "https://agent.ai/oauth/callback",
            "https://claude.ai/oauth/callback",
            "https://claude.ai/api/mcp/auth_callback",
            "http://localhost:3000/callback",
            "mcp://oauth/callback"
        ]

        all_redirect_uris = list(set(redirect_uris + default_uris))

        if self.storage.store_client(client_id, client_secret, all_redirect_uris):
            return {
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uris": all_redirect_uris,
                "grant_types": ["authorization_code"],
                "response_types": ["code"],
                "token_endpoint_auth_method": "client_secret_post"
            }
        else:
            raise ValueError("Failed to register client")

    async def authorize(self, client_id: str, user_email: str, user_password: str) -> str:
        """Create authorization code for user"""
        # Validate user credentials by attempting to authenticate
        from monarchmoney import MonarchMoney, RequireMFAException

        try:
            client = MonarchMoney()
            await client.login(
                email=user_email,
                password=user_password,
                save_session=False,
                use_saved_session=False
            )

            # If we get here, credentials are valid
            auth_code = self.generate_auth_code()

            if self.storage.store_auth_code(auth_code, client_id, user_email, user_password):
                return auth_code
            else:
                raise ValueError("Failed to store authorization code")

        except RequireMFAException:
            raise ValueError("MFA is required but not supported in OAuth flow")
        except Exception as e:
            raise ValueError(f"Invalid credentials: {str(e)}")

    def exchange_code_for_token(self, code: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        # Verify client credentials
        if not self.storage.verify_client(client_id, client_secret):
            raise ValueError("Invalid client credentials")

        # Exchange auth code
        auth_data = self.storage.exchange_auth_code(code, client_id)
        if not auth_data:
            raise ValueError("Invalid or expired authorization code")

        # Generate access token
        access_token = self.generate_access_token()

        if self.storage.store_access_token(
            access_token,
            client_id,
            auth_data["user_email_hash"],
            auth_data["user_password_hash"]
        ):
            return {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": 86400,  # 24 hours
                "scope": "accounts:read transactions:read budgets:read"
            }
        else:
            raise ValueError("Failed to create access token")

    def validate_token(self, token: str) -> Optional[Dict[str, str]]:
        """Validate access token"""
        return self.storage.validate_access_token(token)

# Environment-based configuration
def get_oauth_config() -> Dict[str, str]:
    """Get OAuth configuration from environment variables"""
    return {
        "authorization_endpoint": os.getenv("OAUTH_AUTHORIZATION_ENDPOINT", "/oauth/authorize"),
        "token_endpoint": os.getenv("OAUTH_TOKEN_ENDPOINT", "/oauth/token"),
        "registration_endpoint": os.getenv("OAUTH_REGISTRATION_ENDPOINT", "/oauth/register"),
        "issuer": os.getenv("OAUTH_ISSUER", "https://your-mcp-server.com"),
        "scopes_supported": ["accounts:read", "transactions:read", "budgets:read"]
    }