# 🚀 FastMCP Setup - Monarch Money MCP Server

This is a **much simpler** MCP server implementation using FastMCP that's designed to work with STDIO transport (the standard way MCP clients connect).

## ✅ **Simple Connection Method**

### For Claude Desktop (Recommended)

1. **Add to your MCP settings** in Claude Desktop:
   ```json
   {
     "mcpServers": {
       "monarchmoney": {
         "command": "uv",
         "args": ["run", "fastmcp_server.py"],
         "cwd": "/Users/CESARMAC/Desktop/ENV/monarchmoney-mcp",
         "env": {
           "MONARCH_EMAIL": "bcqyg42yby@privaterelay.appleid.com",
           "MONARCH_PASSWORD": "$5D!9Cx9Dc*z7Yw"
         }
       }
     }
   }
   ```

2. **Restart Claude Desktop** - it will automatically connect to your server

### For Other MCP Clients

Use these connection details:
- **Command**: `uv run fastmcp_server.py`
- **Working Directory**: `/Users/CESARMAC/Desktop/ENV/monarchmoney-mcp`
- **Transport**: STDIO
- **Environment Variables**: Set MONARCH_EMAIL and MONARCH_PASSWORD

## 🛠️ **Available Tools**

Once connected, you'll have access to:

1. **`get_accounts()`** - Get all your Monarch Money accounts with balances
2. **`get_transactions(start_date?, end_date?, limit?, account_id?)`** - Get transactions with optional filtering
3. **`get_budgets()`** - Get your budget information
4. **`get_spending_plan(month?)`** - Get spending plan for a specific month
5. **`get_account_history(account_id, start_date?, end_date?)`** - Get balance history for an account

## 🎯 **Why FastMCP is Better**

- **No OAuth complexity** - Direct STDIO connection
- **No HTTP endpoints** - Works exactly how MCP was designed
- **Automatic discovery** - Claude Desktop finds it automatically
- **Simpler code** - Just decorators on async functions
- **Better reliability** - No network issues, timeouts, or HTTP errors

## 🧪 **Local Testing**

To test the server locally:

```bash
# Install dependencies
uv sync

# Set environment variables
export MONARCH_EMAIL="bcqyg42yby@privaterelay.appleid.com"
export MONARCH_PASSWORD="$5D!9Cx9Dc*z7Yw"

# Run the server
uv run fastmcp_server.py
```

The server will start and wait for MCP client connections via STDIO.

## 🔧 **Troubleshooting**

### "Authentication failed"
- Check your MONARCH_EMAIL and MONARCH_PASSWORD environment variables
- If you have MFA enabled, set MONARCH_MFA_SECRET

### "Command not found: uv"
- Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Restart your terminal

### Claude Desktop doesn't see the server
- Check the JSON syntax in your MCP settings
- Ensure the `cwd` path is correct for your system
- Restart Claude Desktop after making changes

## 🌐 **HTTP Endpoints (Still Available)**

The old HTTP endpoints are still available at:
- https://cesar-money-mcp.vercel.app/api (MCP over HTTP)
- https://cesar-money-mcp.vercel.app/api/accounts (REST API)

But **FastMCP with STDIO is the recommended approach** for MCP clients!

## 📝 **Configuration File Location**

Claude Desktop MCP settings file locations:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

## 🎉 **Success!**

Once connected, you can ask Claude things like:
- "Show me my account balances"
- "What were my transactions last month?"
- "Get my spending plan for December"
- "Show transaction history for my checking account"

Claude will automatically use the appropriate MCP tools to fetch your Monarch Money data!