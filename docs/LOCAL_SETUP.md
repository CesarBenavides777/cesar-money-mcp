# 🏠 Local FastMCP Setup (Recommended)

Since the HTTP OAuth endpoints are having deployment issues, here's the **local FastMCP setup** that will work perfectly with your MCP client.

## 🚀 **Quick Local Setup**

### 1. Run the FastMCP Server Locally

```bash
# Navigate to project directory
cd /Users/CESARMAC/Desktop/ENV/monarchmoney-mcp

# Set your credentials
export MONARCH_EMAIL="bcqyg42yby@privaterelay.appleid.com"
export MONARCH_PASSWORD="$5D!9Cx9Dc*z7Yw"

# Run the FastMCP server
uv run fastmcp_server.py
```

### 2. Connect Your MCP Client

**Server URL**: `http://localhost:8000` or use STDIO connection

**For STDIO (Recommended)**:
```
Command: uv run fastmcp_server.py
Working Directory: /Users/CESARMAC/Desktop/ENV/monarchmoney-mcp
Environment:
  MONARCH_EMAIL=bcqyg42yby@privaterelay.appleid.com
  MONARCH_PASSWORD=$5D!9Cx9Dc*z7Yw
```

## 🔧 **Alternative: HTTP Server with FastMCP**

If your platform needs HTTP, run FastMCP with HTTP transport:

```bash
# Run with HTTP transport
uv run python -c "
from fastmcp_server import mcp
import uvicorn

# Run FastMCP as HTTP server
app = mcp.create_app()
uvicorn.run(app, host='0.0.0.0', port=8000)
"
```

Then connect to: `http://localhost:8000`

## 🌐 **For Remote Access**

If you need remote access, use ngrok:

```bash
# Install ngrok
brew install ngrok

# Run FastMCP server
uv run fastmcp_server.py &

# Expose it
ngrok http 8000
```

Use the ngrok URL for remote access.

## 💡 **Why Local is Better**

1. **No Deployment Issues** - Runs directly with FastMCP
2. **Full Control** - Set environment variables easily
3. **Real-time Updates** - No deployment delays
4. **Better Debugging** - See logs directly
5. **Native MCP** - FastMCP as designed

## 🛠️ **Available Tools (Same as HTTP)**

- `get_accounts()` - Get all accounts
- `get_transactions(start_date?, end_date?, limit?, account_id?)` - Get transactions
- `get_budgets()` - Get budget info
- `get_spending_plan(month?)` - Get spending plan
- `get_account_history(account_id, start_date?, end_date?)` - Get account history

## 🎯 **Recommended Approach**

**For Development/Testing**: Use local FastMCP server
**For Production**: Once HTTP OAuth is working, use Vercel deployment

The local server will work immediately without any HTTP OAuth complications!