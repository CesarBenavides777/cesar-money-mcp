# Monarch Money MCP Server

> Open-source MCP server that connects AI assistants to your Monarch Money financial data.

A TypeScript [Model Context Protocol](https://modelcontextprotocol.io/) server that gives Claude, GPTs, and other AI assistants real-time access to your accounts, transactions, budgets, net worth, and more -- plus AI-powered analysis tools for spending breakdowns, anomaly detection, cash flow forecasting, subscription tracking, and financial health scoring.

---

## Features

- **20+ tools** covering accounts, transactions, budgets, cash flow, categories, institutions, recurring payments, and net worth
- **AI-powered analysis** -- spending breakdowns, anomaly detection, cash flow forecasting, subscription tracking, trend detection, and a composite financial health score
- **Dual transport** -- stdio for Claude Desktop / Claude Code and HTTP (Streamable HTTP) for Claude Custom Connectors and remote clients
- **OAuth 2.1 with PKCE** for secure remote access, including Dynamic Client Registration (RFC 7591) and Authorization Server Metadata (RFC 8414)
- **MCP Resources** -- structured `finance://` URIs for direct data access
- **MCP Prompts** -- five canned analysis templates (monthly review, budget check, spending audit, net worth update, subscription audit)
- **Built with Bun, Hono, TypeScript, and the official MCP SDK**

---

## Quick Start

### Prerequisites

| Requirement | Version | Link |
|---|---|---|
| Bun | >= 1.0 | https://bun.sh |
| Monarch Money account | -- | https://monarchmoney.com |

### Installation

```bash
git clone https://github.com/cesarmac/monarch-money-mcp.git
cd monarch-money-mcp
cp .env.example .env   # Edit with your Monarch Money credentials
bun install
```

### Claude Desktop / Claude Code (stdio)

Add the server to your `claude_desktop_config.json`:

```jsonc
{
  "mcpServers": {
    "monarch-money": {
      "command": "bun",
      "args": ["src/index.ts", "--transport", "stdio"],
      "cwd": "/absolute/path/to/monarch-money-mcp",
      "env": {
        "MONARCH_EMAIL": "you@example.com",
        "MONARCH_PASSWORD": "your-password",
        "MONARCH_MFA_SECRET": "your-totp-secret"
      }
    }
  }
}
```

Restart Claude Desktop. The Monarch Money tools will appear in the tool picker.

### Remote / HTTP Mode

Start the server on port 3200:

```bash
bun start:http
# Monarch Money MCP server listening on http://localhost:3200
```

Verify it is running:

```bash
curl http://localhost:3200/health
# {"status":"ok","server":"monarch-money-mcp","version":"1.0.0"}
```

Send MCP requests to `POST /mcp`. The server will return a `Mcp-Session-Id` header for session continuity.

---

## Available Tools

### Data Tools

| Tool | Description |
|---|---|
| `get_accounts` | List all linked financial accounts with balances, types, and institution details |
| `get_account_history` | Get balance history for a specific account over a date range |
| `get_transactions` | Retrieve paginated transactions with filters (date, category, account) |
| `search_transactions` | Search transactions by merchant name or description text |
| `get_budgets` | Get budget data with planned amounts, actual spending, and remaining balances |
| `get_cashflow` | Detailed cash flow with category-level income and expense breakdowns |
| `get_cashflow_summary` | High-level income vs. expenses totals and net savings/deficit |
| `get_recurring_transactions` | All recurring transactions: subscriptions, bills, and regular payments |
| `get_categories` | All transaction categories with IDs and types (income vs. expense) |
| `get_category_groups` | Hierarchical category groups (e.g., "Food & Drink" containing "Groceries") |
| `get_institutions` | Linked financial institutions with connection status and sync info |
| `get_net_worth` | Current net worth snapshot: total assets, liabilities, and net worth |
| `get_net_worth_history` | Net worth time series for charting growth and tracking progress |

### Analysis Tools

| Tool | Description |
|---|---|
| `analyze_spending` | Category breakdowns, top merchants, daily averages, period-over-period comparison |
| `detect_anomalies` | Unusually large purchases, potential duplicates, unfamiliar merchants, outlier detection |
| `forecast_cashflow` | Project future balances at 30/60/90-day horizons based on historical patterns |
| `track_subscriptions` | Active subscriptions, price changes, total monthly/annual costs, unused service detection |
| `detect_trends` | Multi-month spending trends by category with direction and magnitude |
| `get_financial_health_score` | Composite 0-100 score based on savings rate, debt ratio, emergency fund, budget adherence, and more |

---

## MCP Resources

Read-only data surfaces accessible via `finance://` URIs.

| Resource | URI | Description |
|---|---|---|
| Accounts | `finance://accounts` | All linked accounts with current balances |
| Net Worth | `finance://net-worth` | Net worth snapshot with asset/liability breakdown and history |
| Current Budget | `finance://budget/current` | Current month budget with planned vs. actual |
| Subscriptions | `finance://subscriptions` | All recurring payments and subscription data |

---

## MCP Prompts

Pre-built analysis templates that chain multiple tools into a structured report.

| Prompt | Description |
|---|---|
| `monthly-review` | Comprehensive monthly review: accounts, cash flow, spending, anomalies, health score |
| `budget-check` | Budget adherence check with over/under alerts and pace projection |
| `spending-audit` | Deep spending audit with trends, subscriptions, anomalies, and savings opportunities |
| `net-worth-update` | Net worth tracking with asset allocation, debt status, and growth trajectory |
| `subscription-audit` | Recurring payment review with price changes, duplicates, and cost optimization |

---

## Deployment

### Docker

```bash
docker build -t monarch-money-mcp .
docker run -p 3200:3200 \
  -e MONARCH_EMAIL="you@example.com" \
  -e MONARCH_PASSWORD="your-password" \
  -e MONARCH_MFA_SECRET="your-totp-secret" \
  -e TRANSPORT=http \
  monarch-money-mcp
```

### Fly.io

The repository includes a `fly.toml` pre-configured for Fly.io. Deploy with:

```bash
fly launch          # First time -- creates the app
fly secrets set \
  MONARCH_EMAIL="you@example.com" \
  MONARCH_PASSWORD="your-password" \
  MONARCH_MFA_SECRET="your-totp-secret"
fly deploy
```

The Fly config uses a shared-cpu-1x VM with 256 MB memory, auto-stop/start, and a persistent volume mounted at `/data` for the SQLite token store.

---

## Configuration

All configuration is via environment variables. Copy `.env.example` to `.env` and edit.

| Variable | Required | Default | Description |
|---|---|---|---|
| `MONARCH_EMAIL` | Yes | -- | Your Monarch Money email |
| `MONARCH_PASSWORD` | Yes | -- | Your Monarch Money password |
| `MONARCH_MFA_SECRET` | No | -- | TOTP secret for MFA-enabled accounts |
| `PORT` | No | `3200` | HTTP server port |
| `TRANSPORT` | No | `stdio` | Transport mode: `stdio` or `http` |
| `OAUTH_CLIENT_ID` | No | -- | OAuth client ID (HTTP mode only) |
| `OAUTH_CLIENT_SECRET` | No | -- | OAuth client secret (HTTP mode only) |
| `CORS_ORIGINS` | No | `https://claude.ai,...` | Comma-separated allowed origins |
| `RATE_LIMIT_RPM` | No | `60` | Maximum requests per minute per IP |
| `LOG_LEVEL` | No | `info` | Logging verbosity |

---

## Architecture

```
monarch-money-mcp/
├── src/
│   ├── index.ts               # Entry point -- stdio or HTTP startup
│   ├── config.ts              # Environment and CLI config loading
│   ├── monarch/
│   │   └── client.ts          # Singleton Monarch Money API client
│   ├── mcp/
│   │   ├── server.ts          # MCP server factory (registers all tools/resources/prompts)
│   │   └── transport.ts       # HTTP transport bridge for Hono
│   ├── tools/
│   │   ├── accounts.ts        # get_accounts, get_account_history
│   │   ├── transactions.ts    # get_transactions, search_transactions
│   │   ├── budgets.ts         # get_budgets
│   │   ├── cashflow.ts        # get_cashflow, get_cashflow_summary
│   │   ├── recurring.ts       # get_recurring_transactions
│   │   ├── categories.ts      # get_categories, get_category_groups
│   │   ├── institutions.ts    # get_institutions
│   │   ├── insights.ts        # get_net_worth, get_net_worth_history
│   │   ├── analysis.ts        # Analysis tool wrappers
│   │   ├── resources.ts       # MCP resource definitions
│   │   └── prompts.ts         # MCP prompt templates
│   ├── analysis/
│   │   ├── spending.ts        # Spending breakdowns
│   │   ├── anomalies.ts       # Anomaly detection
│   │   ├── forecasting.ts     # Cash flow forecasting
│   │   ├── subscriptions.ts   # Subscription analysis
│   │   ├── trends.ts          # Trend detection
│   │   ├── health.ts          # Financial health scoring
│   │   └── index.ts           # Barrel exports
│   ├── oauth/
│   │   ├── routes.ts          # OAuth endpoints (metadata, register, authorize, token)
│   │   ├── provider.ts        # Monarch credential validation
│   │   └── store.ts           # SQLite-backed token/client store
│   └── middleware/
│       ├── auth.ts            # Bearer token validation
│       ├── rate-limit.ts      # Per-IP sliding-window rate limiter
│       └── audit.ts           # Structured JSON audit logging
├── Dockerfile                 # Production Docker image (oven/bun)
├── fly.toml                   # Fly.io deployment config
├── tsconfig.json              # TypeScript configuration
├── package.json               # Dependencies and scripts
└── .env.example               # Environment variable template
```

The server cleanly separates concerns:

- **`src/monarch/`** -- API client singleton with session caching, auto-retry, and response caching
- **`src/tools/`** -- Each file registers tools via `registerXxxTools(server)`. All tools follow the same error-handling pattern.
- **`src/analysis/`** -- Pure functions with no MCP or API dependencies. Easy to unit test.
- **`src/oauth/`** -- Full OAuth 2.1 authorization code flow with PKCE, dynamic client registration, and SQLite persistence.
- **`src/middleware/`** -- Hono middleware for auth, rate limiting, and audit logging.

---

## Contributing

Contributions are welcome. To get started:

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Install dependencies: `bun install`
4. Make your changes
5. Run type checks: `bun check-types`
6. Run tests: `bun test`
7. Submit a pull request

Please keep PRs focused on a single concern and include tests for new functionality.

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Connector Support

This server works with multiple AI platforms:

### Claude Desktop (stdio)

Use the `claude_desktop_config.json` configuration shown in [Quick Start](#claude-desktop--claude-code-stdio). The server communicates over stdin/stdout with no network required.

### Claude Custom Connectors (HTTP + OAuth)

Run in HTTP mode and point a Claude Custom Connector at your deployment URL. The server implements:

- `GET /.well-known/oauth-authorization-server` -- RFC 8414 metadata discovery
- `POST /oauth/register` -- RFC 7591 dynamic client registration
- `GET/POST /oauth/authorize` -- Authorization endpoint with PKCE
- `POST /oauth/token` -- Token endpoint (authorization_code + refresh_token grants)
- `POST /mcp` -- Streamable HTTP MCP endpoint

### OpenAI Custom GPTs

The `/api/v1/` REST endpoints can be consumed by OpenAI Custom GPTs or any HTTP client. Use the health endpoint at `GET /api/v1/health` to verify connectivity.

### Other MCP Clients

Any MCP-compatible client can connect via either the stdio or HTTP transport. The server advertises its full tool, resource, and prompt catalog through standard MCP discovery.

---

## Roadmap

- Native macOS app with SwiftUI -- a paid desktop client with a polished UI for a personal finance dashboard powered by this server
- Widget support for iOS and macOS (account balances, budget status, net worth at a glance)
- MCP registry publishing (Smithery, Glama)
- Additional data sources beyond Monarch Money

---

## Acknowledgments

- [Monarch Money](https://monarchmoney.com) for the financial data platform
- [Model Context Protocol](https://modelcontextprotocol.io/) by Anthropic
- [Bun](https://bun.sh), [Hono](https://hono.dev), and the TypeScript ecosystem
