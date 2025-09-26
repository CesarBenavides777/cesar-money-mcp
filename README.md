# Monarch Money MCP Server 💰

A Model Context Protocol (MCP) server that provides secure access to your Monarch Money financial data through Claude or any MCP-compatible client.

## 🌟 Features

- **5 Core Financial Tools**:
  - `get_accounts` - View all your financial accounts with balances
  - `get_transactions` - Search and filter transaction history
  - `get_budgets` - Access budget information and categories
  - `get_spending_plan` - Review monthly spending plans
  - `get_account_history` - Track account balance history over time

- **Multiple Authentication Methods**:
  - OAuth 2.0 flow (recommended for production)
  - Environment variables (for development)
  - Interactive credentials input (for testing)

- **Multiple Deployment Options**:
  - Vercel serverless deployment
  - Local development server
  - Docker containerization (coming soon)

## 🚀 Quick Start

### Option 1: Deploy to Vercel (Recommended)

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/yourusername/monarchmoney-mcp)

See [Vercel Deployment Guide](docs/DEPLOY_VERCEL.md) for detailed instructions.

### Option 2: Local Development

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/monarchmoney-mcp.git
   cd monarchmoney-mcp
   ```

2. **Install dependencies**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Run tests** (no credentials needed for initial test):
   ```bash
   python tests/test_all_tools.py
   ```

4. **Start the server**:
   ```bash
   python fastmcp_server.py
   ```

See [Local Setup Guide](docs/LOCAL_SETUP.md) for more details.

## 🧪 Testing

### Comprehensive Test Suite

The project includes a comprehensive test suite that works with multiple authentication methods:

```bash
# Test with OAuth credentials (interactive)
python tests/test_all_tools.py

# Test with command-line credentials
python tests/test_all_tools.py your_email@example.com your_password [mfa_secret]

# Test with environment variables
export MONARCH_EMAIL=your_email@example.com
export MONARCH_PASSWORD=your_password
export MONARCH_MFA_SECRET=your_mfa_secret  # Optional
python tests/test_all_tools.py
```

### Test Coverage

The test suite covers:
- ✅ Connection and authentication
- ✅ All 5 MCP tools
- ✅ OAuth flow integration
- ✅ Error handling
- ✅ Data validation

## 📚 Documentation

### Setup Guides
- [Local Development Setup](docs/LOCAL_SETUP.md) - Get started locally
- [Vercel Deployment](docs/DEPLOY_VERCEL.md) - Deploy to production
- [FastMCP Configuration](docs/FASTMCP_SETUP.md) - FastMCP framework details

### OAuth Integration
- [OAuth Setup Guide](docs/OAUTH_SETUP.md) - Basic OAuth implementation
- [OAuth with FastMCP](docs/OAUTH_FASTMCP_SETUP.md) - Advanced OAuth integration

## 🏗️ Project Structure

```
monarchmoney-mcp/
├── api/                    # API endpoints
│   ├── mcp.py             # Main MCP JSON-RPC endpoint
│   ├── oauth-working.py   # OAuth implementation
│   └── ...
├── docs/                   # Documentation
│   ├── DEPLOY_VERCEL.md
│   ├── LOCAL_SETUP.md
│   └── ...
├── tests/                  # Test suite
│   ├── test_all_tools.py # Comprehensive test suite
│   ├── integration/       # Integration tests
│   └── utils/             # Test utilities
├── fastmcp_server.py      # Main FastMCP server
├── fastmcp_oauth_server.py # OAuth-enabled server
├── requirements.txt       # Python dependencies
├── vercel.json           # Vercel configuration
└── README.md             # This file
```

## 🔐 Security

### Best Practices

1. **Never commit credentials** to version control
2. **Use OAuth flow** for production deployments
3. **Enable MFA** on your Monarch Money account
4. **Use HTTPS** for all API endpoints
5. **Rotate tokens** regularly

### Environment Variables

If using environment variables (development only):

```bash
# .env file (never commit this!)
MONARCH_EMAIL=your_email@example.com
MONARCH_PASSWORD=your_password
MONARCH_MFA_SECRET=your_mfa_secret  # Optional
```

## 🛠️ API Reference

### MCP Tools

#### `get_accounts()`
Returns all financial accounts with current balances.

#### `get_transactions(start_date?, end_date?, limit?, account_id?)`
Fetches transactions with optional filtering.

#### `get_budgets()`
Retrieves budget information and categories.

#### `get_spending_plan(month?)`
Gets spending plan for specified month (default: current month).

#### `get_account_history(account_id, start_date?, end_date?)`
Returns balance history for a specific account.

### JSON-RPC Endpoints

```javascript
// List available tools
{
  "jsonrpc": "2.0",
  "method": "tools/list",
  "id": 1
}

// Call a tool
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "get_transactions",
    "arguments": {
      "start_date": "2025-01-01",
      "end_date": "2025-01-31",
      "limit": 50
    }
  },
  "id": 2
}
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Setup

1. Fork the repository
2. Create a feature branch
3. Run tests: `python tests/test_all_tools.py`
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Monarch Money](https://monarchmoney.com) for the excellent financial platform
- [FastMCP](https://github.com/jlowin/fastmcp) for the MCP framework
- [Anthropic](https://anthropic.com) for the MCP specification

## 🐛 Troubleshooting

### Common Issues

**Issue**: "FunctionTool object is not callable"
- **Solution**: Update to latest version, this has been fixed

**Issue**: "Monarch credentials not configured"
- **Solution**: Use OAuth flow or set environment variables

**Issue**: "MFA is required"
- **Solution**: Provide MFA secret or disable MFA temporarily for testing

For more issues, check our [Troubleshooting Guide](docs/TROUBLESHOOTING.md) or open an issue.

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/monarchmoney-mcp/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/monarchmoney-mcp/discussions)
- **Email**: support@example.com

---

Built with ❤️ for the Monarch Money community