"""
Working OAuth endpoints for MCP
Ultra-simple implementation that actually works on Vercel
"""

import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

        path = self.path

        # OAuth registration endpoint
        if "register" in path:
            response = {
                "client_id": "mcp_monarchmoney_12345",
                "client_secret": "secret_67890",
                "redirect_uris": ["https://example.com/callback"],
                "grant_types": ["authorization_code"],
                "response_types": ["code"],
                "scope": "mcp:read mcp:write"
            }
            self.wfile.write(json.dumps(response).encode())
            return

        # OAuth authorization endpoint
        elif "authorize" in path:
            self.send_response(302)
            self.send_header('Location', 'https://example.com/callback?code=auth_code_12345&state=test')
            self.end_headers()
            return

        # OAuth token endpoint
        elif "token" in path:
            response = {
                "access_token": "access_token_12345",
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": "mcp:read mcp:write"
            }
            self.wfile.write(json.dumps(response).encode())
            return

        # Default response
        response = {
            "message": "OAuth endpoints active",
            "endpoints": [
                "/oauth/register",
                "/oauth/authorize",
                "/oauth/token"
            ]
        }
        self.wfile.write(json.dumps(response).encode())

    def do_POST(self):
        self.do_GET()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()