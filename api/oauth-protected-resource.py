"""
OAuth 2.0 Protected Resource Metadata endpoint (RFC 9728)
For MCP server authorization discovery
"""

import json
import os
import logging
from http.server import BaseHTTPRequestHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle OAuth 2.0 Protected Resource Metadata requests"""
        try:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
            self.end_headers()

            # Get base URL from environment or auto-detect from request
            base_url = os.getenv("BASE_URL")
            if not base_url:
                # Auto-detect from request headers (secure fallback)
                host = self.headers.get('Host')
                if host:
                    # Use HTTPS in production, HTTP only for localhost
                    protocol = 'http' if 'localhost' in host or '127.0.0.1' in host else 'https'
                    base_url = f"{protocol}://{host}"
                else:
                    # Final fallback
                    base_url = "https://cesar-money-mcp.vercel.app"

            # OAuth 2.0 Protected Resource Metadata (RFC 9728)
            metadata_response = {
                "resource": base_url,
                "authorization_servers": [base_url],
                "bearer_methods_supported": ["header"],
                "resource_documentation": f"{base_url}/docs",
                "scopes_supported": ["mcp:read", "mcp:write", "accounts:read", "transactions:read", "budgets:read"]
            }

            self.wfile.write(json.dumps(metadata_response, indent=2).encode())

        except Exception as e:
            logger.error(f"Protected resource metadata endpoint error: {e}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            error_response = {
                "error": "server_error",
                "error_description": f"Metadata discovery failed: {str(e)}"
            }
            self.wfile.write(json.dumps(error_response).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()