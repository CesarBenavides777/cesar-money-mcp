# 🚀 Deploying Monarch Money MCP to Vercel

This guide walks you through deploying your Monarch Money MCP server to Vercel with secure API key authentication.

## 📋 Prerequisites

1. Vercel account (free tier works)
2. Vercel CLI installed: `npm i -g vercel`
3. Your Monarch Money credentials

## 🔐 Security Features

- **API Key Authentication**: Additional layer beyond Monarch credentials
- **HTTPS Only**: Vercel provides automatic SSL
- **Environment Variables**: Credentials stored securely in Vercel
- **No Session Persistence**: Each request authenticates fresh

## 📦 Files Created

- `api/index.py` - Serverless function handling all API requests
- `vercel.json` - Vercel configuration
- `requirements.txt` - Python dependencies
- `.env.vercel` - Environment variables (DO NOT COMMIT)

## 🛠️ Deployment Steps

### 1. Install Vercel CLI
```bash
npm i -g vercel
```

### 2. Login to Vercel
```bash
vercel login
```

### 3. Deploy to Vercel
```bash
vercel
```

Follow the prompts:
- Setup and deploy? **Y**
- Which scope? **Select your account**
- Link to existing project? **N**
- Project name? **monarchmoney-mcp** (or your choice)
- Directory? **./** (current directory)
- Want to override settings? **N**

### 4. Set Environment Variables

Go to your [Vercel Dashboard](https://vercel.com/dashboard):
1. Select your project
2. Go to **Settings** → **Environment Variables**
3. Add these variables:

```
API_KEY = ZPl_OHHFyWwQBW0kHgoT-ipM8_6IWWrrmStXPJG0mIg
MONARCH_EMAIL = bcqyg42yby@privaterelay.appleid.com
MONARCH_PASSWORD = $5D!9Cx9Dc*z7Yw
```

Optional (if you have MFA enabled):
```
MONARCH_MFA_SECRET = your-mfa-secret
```

### 5. Redeploy with Environment Variables
```bash
vercel --prod
```

## 🔌 API Endpoints

Your API will be available at: `https://your-project.vercel.app`

### Available Endpoints

#### Get Accounts
```bash
curl -X GET https://your-project.vercel.app/api/accounts \
  -H "X-API-Key: ZPl_OHHFyWwQBW0kHgoT-ipM8_6IWWrrmStXPJG0mIg"
```

#### Get Transactions
```bash
curl -X GET "https://your-project.vercel.app/api/transactions?limit=50&start_date=2024-01-01" \
  -H "X-API-Key: ZPl_OHHFyWwQBW0kHgoT-ipM8_6IWWrrmStXPJG0mIg"
```

#### Get Budgets
```bash
curl -X GET https://your-project.vercel.app/api/budgets \
  -H "X-API-Key: ZPl_OHHFyWwQBW0kHgoT-ipM8_6IWWrrmStXPJG0mIg"
```

#### Get Spending Plan
```bash
curl -X GET https://your-project.vercel.app/api/spending-plan \
  -H "X-API-Key: ZPl_OHHFyWwQBW0kHgoT-ipM8_6IWWrrmStXPJG0mIg"
```

## 🔒 Security Best Practices

1. **Keep API Key Secret**: Never commit `.env.vercel` to git
2. **Rotate Keys Regularly**: Generate new API keys periodically
3. **Use Environment Variables**: Never hardcode credentials
4. **Monitor Usage**: Check Vercel logs for unauthorized access
5. **Restrict CORS**: Update `vercel.json` to limit origins in production

## 🧪 Testing Your Deployment

Test your deployment with this simple script:

```python
import requests

API_KEY = "ZPl_OHHFyWwQBW0kHgoT-ipM8_6IWWrrmStXPJG0mIg"
BASE_URL = "https://your-project.vercel.app"

headers = {"X-API-Key": API_KEY}

# Test accounts endpoint
response = requests.get(f"{BASE_URL}/api/accounts", headers=headers)
print(f"Accounts: {response.status_code}")
print(response.json())
```

## 📊 Monitoring

- View logs: `vercel logs`
- View function metrics in Vercel Dashboard
- Set up alerts for errors or high usage

## 🔄 Updating

To update your deployment:

1. Make changes locally
2. Test with `vercel dev`
3. Deploy with `vercel --prod`

## ⚠️ Important Notes

- **Rate Limits**: Vercel free tier has limits (100GB bandwidth, 100k requests/month)
- **Function Timeout**: Set to 30 seconds (max for free tier)
- **Cold Starts**: First request may be slower
- **MFA**: If you enable MFA on Monarch, add the secret to environment variables

## 🆘 Troubleshooting

### 401 Unauthorized
- Check API key in request headers
- Verify API_KEY environment variable in Vercel

### 500 Internal Error
- Check Vercel function logs: `vercel logs`
- Verify all environment variables are set
- Check Monarch credentials are correct

### Function Timeout
- Monarch API might be slow
- Consider implementing caching
- Upgrade Vercel plan for longer timeouts

## 📝 License

Use at your own risk. Secure your credentials properly!