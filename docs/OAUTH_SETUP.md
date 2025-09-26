# 🔐 OAuth Setup for Monarch Money MCP

This API now supports OAuth 2.0-style authentication with JWT tokens, allowing secure access from multiple services.

## 🚀 Quick Start

### 1. Generate Your Admin Password Hash

First, you need to create a password hash for secure authentication:

```python
import hashlib
password = "your-secure-admin-password"
password_hash = hashlib.sha256(password.encode()).hexdigest()
print(password_hash)
```

### 2. Set Environment Variables in Vercel

Add these to your Vercel project settings:

```bash
# OAuth Configuration
JWT_SECRET=<generate-a-secure-random-string>
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=<your-password-hash-from-step-1>
TOKEN_EXPIRY_HOURS=24

# Keep existing variables
API_KEY=ZPl_OHHFyWwQBW0kHgoT-ipM8_6IWWrrmStXPJG0mIg
MONARCH_EMAIL=bcqyg42yby@privaterelay.appleid.com
MONARCH_PASSWORD=$5D!9Cx9Dc*z7Yw
```

To generate JWT_SECRET:
```python
import secrets
print(secrets.token_urlsafe(32))
```

### 3. Login Flow

#### Via Web Interface
1. Visit https://cesar-money-mcp.vercel.app/
2. Enter your admin username and password
3. Click "Generate Access Token"
4. Copy the JWT token for use in your applications

#### Via API
```bash
curl -X POST https://cesar-money-mcp.vercel.app/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "your-admin-password",
    "client_id": "my-app"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "Bearer",
  "expires_in": 86400,
  "expires_at": "2024-01-02T00:00:00Z",
  "scope": "monarch:read monarch:write"
}
```

## 🔑 Authentication Methods

### Method 1: OAuth Bearer Token (Recommended)
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  https://cesar-money-mcp.vercel.app/api/accounts
```

### Method 2: API Key (Legacy)
```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  https://cesar-money-mcp.vercel.app/api/accounts
```

## 📱 Integration Examples

### Python
```python
import requests

# Login
response = requests.post('https://cesar-money-mcp.vercel.app/api/auth/login', json={
    'username': 'admin',
    'password': 'your-password',
    'client_id': 'python-app'
})
token = response.json()['access_token']

# Use token
headers = {'Authorization': f'Bearer {token}'}
accounts = requests.get('https://cesar-money-mcp.vercel.app/api/accounts', headers=headers)
print(accounts.json())
```

### JavaScript
```javascript
// Login
const loginResponse = await fetch('https://cesar-money-mcp.vercel.app/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        username: 'admin',
        password: 'your-password',
        client_id: 'js-app'
    })
});
const { access_token } = await loginResponse.json();

// Use token
const accounts = await fetch('https://cesar-money-mcp.vercel.app/api/accounts', {
    headers: { 'Authorization': `Bearer ${access_token}` }
});
console.log(await accounts.json());
```

## 🔄 Token Management

### Check Token Status
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://cesar-money-mcp.vercel.app/api/auth/token
```

Response:
```json
{
  "active": true,
  "sub": "admin",
  "scope": "monarch:read monarch:write",
  "exp": 1704153600,
  "client_id": "my-app"
}
```

## 🛡️ Security Best Practices

1. **Never commit passwords or tokens** to your repository
2. **Use HTTPS only** for all API calls
3. **Rotate JWT_SECRET** periodically
4. **Set appropriate token expiry** (default: 24 hours)
5. **Use unique client_id** for each application
6. **Store tokens securely** in your application

## 🚨 Troubleshooting

### "Configuration Required" Error
- You need to set ADMIN_PASSWORD_HASH in Vercel
- The error response will show your password hash

### "Invalid Credentials" Error
- Check username (default: "admin")
- Verify password is correct
- Ensure ADMIN_PASSWORD_HASH matches your password

### "Invalid Token" Error
- Token may be expired (check exp field)
- JWT_SECRET may have changed
- Token may be malformed

## 📊 API Endpoints

All endpoints require authentication:

- `POST /api/auth/login` - Get access token
- `GET /api/auth/token` - Check token status
- `GET /api/accounts` - List Monarch accounts
- `GET /api/transactions` - Get transactions
- `GET /api/budgets` - Get budgets
- `GET /api/spending-plan` - Get spending plan

## 🔧 Advanced Configuration

### Custom Token Expiry
Set `TOKEN_EXPIRY_HOURS` in environment (default: 24)

### CORS Origins
Set `ALLOWED_ORIGINS` as comma-separated list:
```
ALLOWED_ORIGINS=https://app1.com,https://app2.com
```

### Multiple Users (Future)
The system is designed to support multiple users in the future.
Currently, only one admin user is supported.