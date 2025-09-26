"""
OAuth Login Form for Monarch Money MCP
Serves as a separate endpoint for the login form
"""

import json
import os
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs

# Monarch Money credentials from environment
MONARCH_EMAIL = os.getenv("MONARCH_EMAIL")
MONARCH_PASSWORD = os.getenv("MONARCH_PASSWORD")

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Parse query parameters
        from urllib.parse import urlparse
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)

        # Extract OAuth parameters
        client_id = query_params.get('client_id', [''])[0]
        redirect_uri = query_params.get('redirect_uri', [''])[0]
        state = query_params.get('state', [''])[0]
        error = query_params.get('error', [''])[0]

        # Send HTML response
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()

        error_message = ""
        if error:
            error_message = '''
            <div style="color: red; background: #ffebee; padding: 10px; border-radius: 4px; margin-bottom: 20px;">
                ❌ Invalid credentials. Please check your email and password.
            </div>
            '''

        html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monarch Money MCP Authorization</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 400px;
            margin: 100px auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .form-group {{
            margin-bottom: 15px;
        }}
        label {{
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }}
        input {{
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
        }}
        button {{
            width: 100%;
            padding: 10px;
            background: #007cba;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }}
        button:hover {{
            background: #005a87;
        }}
        .info {{
            background: #f0f0f0;
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 20px;
        }}
        .footer {{
            font-size: 12px;
            color: #666;
            margin-top: 20px;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h2>🏦 Monarch Money MCP Authorization</h2>
        <div class="info">
            <strong>Client:</strong> {client_id}<br>
            <strong>Requesting access to:</strong> Your Monarch Money financial data
        </div>
        {error_message}
        <form method="post" action="/oauth/authorize">
            <input type="hidden" name="client_id" value="{client_id}">
            <input type="hidden" name="redirect_uri" value="{redirect_uri}">
            <input type="hidden" name="state" value="{state}">
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
        <div class="footer">
            Your credentials are verified against your configured Monarch Money account and are not stored.
        </div>
    </div>
</body>
</html>'''

        self.wfile.write(html_content.encode('utf-8'))

    def do_POST(self):
        self.do_GET()