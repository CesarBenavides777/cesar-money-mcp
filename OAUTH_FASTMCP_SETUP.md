# 🔐 FastMCP with True OAuth 2.0 Flow

This FastMCP server supports **real OAuth 2.0** with your Monarch Money credentials passed via URL parameters during the OAuth flow.

## 🚀 **OAuth Flow Overview**

1. **Client Registration** - Your platform registers as an OAuth client
2. **Authorization** - User provides Monarch credentials via URL parameters
3. **Token Exchange** - Platform gets access token
4. **API Calls** - Use access token to call MCP tools

## 📋 **Step-by-Step OAuth Setup**

### Step 1: Register OAuth Client

```bash
# Using FastMCP tool directly
curl -X POST http://localhost:8000/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "oauth_register",
    "arguments": {
      "redirect_uris": ["https://your-platform.com/oauth/callback"],
      "client_name": "Your Platform Name"
    }
  }'
```

Response:
```json
{
  "client_id": "mcp_abc123...",
  "client_secret": "xyz789...",
  "authorization_endpoint": "https://cesar-money-mcp.vercel.app/oauth/authorize",
  "token_endpoint": "https://cesar-money-mcp.vercel.app/oauth/token"
}
```

### Step 2: Authorization with Credentials in URL

Direct your users to this authorization URL with Monarch credentials:

```
https://cesar-money-mcp.vercel.app/oauth/authorize?
  client_id=mcp_abc123...&
  redirect_uri=https://your-platform.com/oauth/callback&
  monarch_email=user@example.com&
  monarch_password=userpassword&
  monarch_mfa_secret=optional_mfa_secret&
  state=your_state_value
```

**URL Parameters:**
- `client_id` - Your registered client ID
- `redirect_uri` - Your callback URL
- `monarch_email` - User's Monarch Money email
- `monarch_password` - User's Monarch Money password
- `monarch_mfa_secret` - Optional MFA secret (if enabled)
- `state` - Your state parameter for CSRF protection

### Step 3: Handle Authorization Callback

Your platform receives the authorization code:
```
https://your-platform.com/oauth/callback?
  code=auth_code_here&
  state=your_state_value
```

### Step 4: Exchange Code for Access Token

```bash
curl -X POST https://cesar-money-mcp.vercel.app/oauth/token \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "authorization_code",
    "code": "auth_code_here",
    "client_id": "mcp_abc123...",
    "client_secret": "xyz789...",
    "redirect_uri": "https://your-platform.com/oauth/callback"
  }'
```

Response:
```json
{
  "access_token": "access_token_here",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "monarch:read monarch:write"
}
```

### Step 5: Use Access Token with MCP Tools

```bash
# Get accounts
curl -X POST http://localhost:8000/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "get_accounts",
    "arguments": {
      "access_token": "access_token_here"
    }
  }'

# Get transactions
curl -X POST http://localhost:8000/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "get_transactions",
    "arguments": {
      "access_token": "access_token_here",
      "limit": 50,
      "start_date": "2024-01-01"
    }
  }'
```

## 🔧 **Platform Integration Examples**

### JavaScript/Node.js
```javascript
// Step 1: Register client
const registration = await fetch('/tools/call', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: 'oauth_register',
    arguments: {
      redirect_uris: ['https://your-platform.com/oauth/callback'],
      client_name: 'Your Platform'
    }
  })
});

const { client_id, client_secret } = await registration.json();

// Step 2: Redirect user to authorization with credentials
const authUrl = `https://cesar-money-mcp.vercel.app/oauth/authorize?` +
  new URLSearchParams({
    client_id,
    redirect_uri: 'https://your-platform.com/oauth/callback',
    monarch_email: userEmail,
    monarch_password: userPassword,
    state: 'csrf_token'
  });

window.location.href = authUrl;

// Step 3: Handle callback and exchange code
const tokenResponse = await fetch('https://cesar-money-mcp.vercel.app/oauth/token', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    grant_type: 'authorization_code',
    code: authCode,
    client_id,
    client_secret,
    redirect_uri: 'https://your-platform.com/oauth/callback'
  })
});

const { access_token } = await tokenResponse.json();

// Step 4: Use access token
const accounts = await fetch('/tools/call', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: 'get_accounts',
    arguments: { access_token }
  })
});
```

### Python
```python
import requests

# Register OAuth client
registration = requests.post('/tools/call', json={
    'name': 'oauth_register',
    'arguments': {
        'redirect_uris': ['https://your-platform.com/oauth/callback'],
        'client_name': 'Your Platform'
    }
})
client_data = registration.json()

# Build authorization URL with credentials
import urllib.parse
auth_params = {
    'client_id': client_data['client_id'],
    'redirect_uri': 'https://your-platform.com/oauth/callback',
    'monarch_email': user_email,
    'monarch_password': user_password,
    'state': 'csrf_token'
}
auth_url = f"https://cesar-money-mcp.vercel.app/oauth/authorize?{urllib.parse.urlencode(auth_params)}"

# Exchange code for token
token_response = requests.post('https://cesar-money-mcp.vercel.app/oauth/token', json={
    'grant_type': 'authorization_code',
    'code': auth_code,
    'client_id': client_data['client_id'],
    'client_secret': client_data['client_secret'],
    'redirect_uri': 'https://your-platform.com/oauth/callback'
})
access_token = token_response.json()['access_token']

# Use access token with MCP tools
accounts = requests.post('/tools/call', json={
    'name': 'get_accounts',
    'arguments': {'access_token': access_token}
})
```

## 🛡️ **Security Considerations**

1. **HTTPS Only** - Always use HTTPS for credential transmission
2. **State Parameter** - Use CSRF protection with state parameter
3. **Token Expiry** - Access tokens expire in 1 hour
4. **Secure Storage** - Never log or store Monarch credentials
5. **Client Secret** - Keep client secrets secure server-side

## 🔧 **Available MCP Tools**

All tools support the `access_token` parameter:

- `get_accounts(access_token)` - Get all accounts
- `get_transactions(access_token, start_date?, end_date?, limit?, account_id?)` - Get transactions
- `get_budgets(access_token)` - Get budget information

## 🎯 **Benefits**

- ✅ **True OAuth 2.0** - Industry standard authorization
- ✅ **Secure Credential Handling** - Credentials only in URL parameters during auth
- ✅ **Platform Agnostic** - Works with any OAuth-capable platform
- ✅ **FastMCP Compliant** - Uses official FastMCP specification
- ✅ **Flexible** - Supports both OAuth and STDIO modes

## 🚀 **Running the Server**

```bash
# For HTTP/OAuth mode
uv run fastmcp_oauth_server.py --transport http --port 8000

# For STDIO mode (Claude Desktop)
uv run fastmcp_oauth_server.py
```

This gives you the best of both worlds: simple STDIO for Claude Desktop and full OAuth for other platforms!