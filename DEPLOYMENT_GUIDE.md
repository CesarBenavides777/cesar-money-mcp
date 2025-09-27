# Claude Custom Connectors Deployment Guide

## Issue Summary
Your local MCP server is now fully compatible with Claude Custom Connectors, but your Vercel deployment is running the old code that doesn't support the required authentication specifications.

## Deployment Test Results
```
❌ Your current deployment (https://cesar-money-mcp.vercel.app):
   - Uses old OAuth format: /oauth?action=register
   - Missing refresh_token grant type
   - No Dynamic Client Registration (RFC 7591)
   - Missing proper WWW-Authenticate headers

✅ Your local server (localhost:8000):
   - Proper OAuth endpoints: /oauth/register, /oauth/token
   - Full grant type support: authorization_code + refresh_token
   - Dynamic Client Registration working
   - Proper security headers and PKCE support
```

## Solution Options

### Option 1: Update Vercel Deployment (Recommended)

1. **Deploy updated code to Vercel**:
   ```bash
   # Make sure your updated claude_connector_server.py is committed
   git add claude_connector_server.py fastmcp_server.py
   git commit -m "Update authentication for Claude Custom Connectors compatibility"
   git push origin main  # This should trigger Vercel deployment
   ```

2. **Verify environment variables in Vercel**:
   - `MONARCH_EMAIL` - Your Monarch Money email
   - `MONARCH_PASSWORD` - Your Monarch Money password
   - `MONARCH_MFA_SECRET` - Your MFA secret (if using MFA)
   - `BASE_URL` - Should be `https://cesar-money-mcp.vercel.app`

3. **Test deployment**:
   ```bash
   python test_deployment.py
   ```

### Option 2: Test Locally with Public URL (Immediate Testing)

If you want to test with Claude immediately while updating your deployment:

1. **Install ngrok** (easiest option):
   - Go to https://ngrok.com/download
   - Sign up for free account
   - Download and install ngrok

2. **Expose your local server**:
   ```bash
   # In a new terminal window
   ngrok http 8000
   ```

3. **Use in Claude**:
   - Copy the HTTPS URL from ngrok (e.g., `https://abcd1234.ngrok.io`)
   - In Claude Custom Connectors, use: `https://abcd1234.ngrok.io/mcp`

## What Fixed the Authentication Issues

### 1. Dynamic Client Registration (RFC 7591)
```python
@app.post("/oauth/register")
async def oauth_register(request: Request):
    # Now generates unique client IDs and validates Claude's request format
    client_id = secrets.token_hex(16)
    return {
        "client_id": client_id,
        "client_name": "claudeai",
        "grant_types": ["authorization_code", "refresh_token"],  # Added refresh_token
        "token_endpoint_auth_method": "none",  # Changed from client_secret_post
        # ... proper Claude format
    }
```

### 2. Proper OAuth Flow with PKCE
```python
@app.get("/oauth/authorize")
async def oauth_authorize(
    # Now validates PKCE parameters
    code_challenge: str = None,
    code_challenge_method: str = None
):
    # Returns HTML consent form instead of JSON
    # Stores PKCE challenge for token validation
```

### 3. Secure Token Exchange
```python
@app.post("/oauth/token")
async def oauth_token(request: Request):
    # Now validates PKCE code_verifier
    # Supports both authorization_code and refresh_token grants
    # Proper token storage and validation
```

### 4. Proper Error Responses
```python
async def get_bearer_token(authorization: str = Header(None)) -> str:
    if not authorization:
        raise HTTPException(
            status_code=401,
            headers={"WWW-Authenticate": 'Bearer realm="mcp"'}  # Added required header
        )
```

## Testing Checklist

Once your deployment is updated:

- [ ] OAuth metadata endpoint works: `GET /.well-known/oauth-authorization-server`
- [ ] Dynamic client registration works: `POST /oauth/register`
- [ ] Authorization form renders: `GET /oauth/authorize`
- [ ] Token exchange works: `POST /oauth/token`
- [ ] MCP discovery works: `GET /mcp`
- [ ] Unauthorized requests return 401 with WWW-Authenticate header
- [ ] Tools list works with valid token: `POST /mcp/rpc`

## Expected Results

After deployment update, you should be able to:

1. Add integration in Claude Custom Connectors
2. Successfully complete OAuth flow
3. See your Monarch Money tools in Claude
4. Query your financial data through Claude

## Common Issues

### "There was an error connecting to Monarch MCP"
- Usually means OAuth flow is failing
- Check that all endpoints return correct status codes
- Verify HTTPS is used (Claude requires HTTPS)

### "NoneType concatenation error"
- Fixed in fastmcp_server.py with ultra-safe string handling
- Make sure both files are deployed together

### "Invalid token format"
- Ensure token validation logic matches token generation
- Check that in-memory storage is properly initialized

## Support

If you continue having issues after deployment:

1. Run `python test_deployment.py` against your updated URL
2. Check Vercel function logs for errors
3. Verify all environment variables are set correctly
4. Test with a tunnel URL to isolate deployment vs. code issues