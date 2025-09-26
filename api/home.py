"""
Serve the login page and homepage for Monarch Money MCP
"""

import os

def handler(event, context):
    """Serve the HTML login page"""

    # Read the HTML file
    html_path = os.path.join(os.path.dirname(__file__), 'login.html')

    try:
        with open(html_path, 'r') as f:
            html_content = f.read()

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "text/html",
                "Cache-Control": "public, max-age=3600"
            },
            "body": html_content
        }
    except FileNotFoundError:
        return {
            "statusCode": 404,
            "headers": {
                "Content-Type": "text/html"
            },
            "body": """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Monarch Money MCP</title>
                <style>
                    body {
                        font-family: -apple-system, system-ui, sans-serif;
                        max-width: 800px;
                        margin: 50px auto;
                        padding: 20px;
                    }
                    h1 { color: #667eea; }
                    .endpoint {
                        background: #f5f5f5;
                        padding: 10px;
                        margin: 10px 0;
                        border-radius: 5px;
                        font-family: monospace;
                    }
                </style>
            </head>
            <body>
                <h1>💜 Monarch Money MCP API</h1>
                <p>OAuth-enabled API for Monarch Money data access.</p>

                <h2>Authentication</h2>
                <p>This API supports two authentication methods:</p>
                <ul>
                    <li><strong>OAuth Token:</strong> POST to /api/auth/login</li>
                    <li><strong>API Key:</strong> Use X-API-Key header</li>
                </ul>

                <h2>Available Endpoints</h2>
                <div class="endpoint">GET /api/accounts</div>
                <div class="endpoint">GET /api/transactions</div>
                <div class="endpoint">GET /api/budgets</div>
                <div class="endpoint">GET /api/spending-plan</div>
                <div class="endpoint">POST /api/auth/login</div>
                <div class="endpoint">GET /api/auth/token</div>

                <h2>Example Usage</h2>
                <pre style="background: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto;">
# With OAuth Token
curl -H "Authorization: Bearer YOUR_TOKEN" \\
  https://cesar-money-mcp.vercel.app/api/accounts

# With API Key
curl -H "X-API-Key: YOUR_API_KEY" \\
  https://cesar-money-mcp.vercel.app/api/accounts</pre>
            </body>
            </html>
            """
        }