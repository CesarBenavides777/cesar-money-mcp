# AGENTS.md — Monarch Money MCP Server

Instructions for AI coding agents (Claude Code, Cursor, Copilot, Windsurf, Cline, etc.) working on this project.

---

## What This Project Is

An open-source TypeScript MCP (Model Context Protocol) server that connects AI assistants to Monarch Money personal finance data. It exposes 20+ tools for accounts, transactions, budgets, cash flow, net worth, recurring payments, and AI-powered financial analysis — plus MCP resources and prompt templates.

**Dual transport:** stdio (for Claude Desktop / Claude Code local use) and HTTP (for Claude Custom Connectors, OpenAI GPTs, and remote deployment via Fly.io).

---

## Tech Stack

| Layer | Technology |
|---|---|
| Runtime | Bun >= 1.0 |
| Language | TypeScript 5.7+ (strict mode, ES2022 target) |
| HTTP framework | Hono |
| MCP | `@modelcontextprotocol/sdk` ^1.12.0 |
| Finance API | `monarchmoney` npm package ^1.1.3 |
| Token storage | SQLite via `bun:sqlite` (WAL mode) |
| Validation | Zod |
| Container | `oven/bun:1` Docker image |
| Deployment | Fly.io (`fly.toml` included) |
| CI/CD | GitHub Actions (`.github/workflows/`) |

---

## Quick Navigation

Use this to find things fast:

| What you're looking for | Where to go |
|---|---|
| Entry point (stdio vs HTTP startup) | `src/index.ts` |
| Environment config | `src/config.ts` |
| Monarch Money API client (singleton) | `src/monarch/client.ts` |
| MCP server factory (tool registration) | `src/mcp/server.ts` |
| HTTP transport bridge (Hono ↔ MCP) | `src/mcp/transport.ts` |
| Data tools (accounts, transactions, etc.) | `src/tools/*.ts` |
| Analysis engine (pure functions) | `src/analysis/*.ts` |
| OAuth 2.1 flow | `src/oauth/routes.ts`, `store.ts`, `provider.ts` |
| Middleware (auth, rate limit, audit) | `src/middleware/*.ts` |
| Tests | `src/**/*.test.ts` (colocated with source) |
| CI pipeline | `.github/workflows/ci.yml` |
| Deploy pipeline | `.github/workflows/deploy.yml` |
| Fly.io config | `fly.toml` |
| Docker build | `Dockerfile` |
| monarchmoney SDK types | `node_modules/monarchmoney/dist/types/` |
| monarchmoney SDK API implementations | `node_modules/monarchmoney/dist/api/` |
| MCP SDK types | `node_modules/@modelcontextprotocol/sdk/dist/esm/server/mcp.d.ts` |

---

## Project Structure

```
src/
├── index.ts                  # Entry point — routes to stdio or HTTP mode
├── config.ts                 # Env vars + CLI flags → typed Config object
├── monarch/
│   └── client.ts             # Singleton MonarchClient (login, session cache, auto-revalidate)
├── mcp/
│   ├── server.ts             # McpServer factory — registers all tools, resources, prompts
│   └── transport.ts          # HttpTransport — bridges Hono POST requests to MCP Transport interface
├── tools/
│   ├── index.ts              # Barrel re-exports
│   ├── accounts.ts           # get_accounts, get_account_history
│   ├── transactions.ts       # get_transactions, search_transactions
│   ├── budgets.ts            # get_budgets
│   ├── cashflow.ts           # get_cashflow, get_cashflow_summary
│   ├── recurring.ts          # get_recurring_transactions
│   ├── categories.ts         # get_categories, get_category_groups
│   ├── institutions.ts       # get_institutions
│   ├── insights.ts           # get_net_worth, get_net_worth_history
│   ├── analysis.ts           # Wires analysis/ functions as MCP tools
│   ├── resources.ts          # finance:// MCP resources
│   └── prompts.ts            # Canned analysis prompt templates
├── analysis/
│   ├── index.ts              # Barrel exports
│   ├── spending.ts           # analyzeSpending()
│   ├── anomalies.ts          # detectAnomalies()
│   ├── forecasting.ts        # forecastCashflow()
│   ├── subscriptions.ts      # analyzeSubscriptions()
│   ├── trends.ts             # detectTrends()
│   └── health.ts             # calculateHealthScore()
├── oauth/
│   ├── routes.ts             # OAuth 2.1 endpoints (Hono router)
│   ├── provider.ts           # Validates Monarch Money credentials
│   └── store.ts              # SQLite token/client store (bun:sqlite)
└── middleware/
    ├── auth.ts               # Bearer token validation
    ├── rate-limit.ts         # Per-IP sliding window rate limiter
    └── audit.ts              # Structured JSON audit logging
```

---

## Commands

| Command | What it does |
|---|---|
| `bun install` | Install dependencies |
| `bun dev` | Watch mode (auto-restart on changes) |
| `bun start` | Start with default transport (stdio) |
| `bun start:stdio` | Start in stdio mode |
| `bun start:http` | Start HTTP server on port 3200 |
| `bun check-types` | TypeScript validation (`tsc --noEmit`) |
| `bun test` | Run test suite (68 tests across 7 files) |

---

## Key Skills for Agents

### 1. Adding a New MCP Tool

Create or edit a file in `src/tools/`. Each file exports a `registerXxxTools(server)` function:

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { getMonarchClient } from "../monarch/client.js";

export function registerMyTools(server: McpServer) {
  server.registerTool(
    "tool_name",
    {
      description: "Clear description of what this tool does and when to use it.",
      inputSchema: {
        param_name: z.string().optional().describe("What this parameter controls."),
      },
      annotations: { readOnlyHint: true },
    },
    async ({ param_name }) => {
      try {
        const client = await getMonarchClient();
        const data = await client.someApi.someMethod();
        return { content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }] };
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        return { content: [{ type: "text" as const, text: `Error: ${message}` }], isError: true };
      }
    }
  );
}
```

Then import and call it in `src/mcp/server.ts`:

```typescript
import { registerMyTools } from "../tools/my-tools.js";
// ... inside createMcpServer():
registerMyTools(server);
```

### 2. Adding an Analysis Function

Analysis functions are **pure** (data in, result out — no API calls, no MCP dependencies):

1. Create the function in `src/analysis/my-analysis.ts`
2. Export it from `src/analysis/index.ts`
3. Wire it as a tool in `src/tools/analysis.ts` — fetch data via `getMonarchClient()`, pass to the pure function, return the result
4. Add a test in `src/analysis/my-analysis.test.ts` — use mock data, no API calls needed

### 3. Adding an MCP Resource

In `src/tools/resources.ts`:

```typescript
server.registerResource(
  "name",
  "finance://uri",
  { description: "What this resource provides" },
  async (uri) => {
    const client = await getMonarchClient();
    const data = await client.someApi.someMethod();
    return { contents: [{ uri: uri.href, mimeType: "application/json", text: JSON.stringify(data, null, 2) }] };
  }
);
```

### 4. Adding an MCP Prompt

In `src/tools/prompts.ts`:

```typescript
server.registerPrompt(
  "prompt-name",
  { description: "What analysis this prompt performs" },
  async () => ({
    messages: [{ role: "user" as const, content: { type: "text" as const, text: "Instructions for the AI..." } }],
  })
);
```

---

## Monarch Money API Reference

All API calls go through `getMonarchClient()` from `src/monarch/client.ts`. Never instantiate `MonarchClient` directly.

```typescript
import { getMonarchClient } from "../monarch/client.js";
const client = await getMonarchClient(); // Singleton, auto-login, session-cached
```

### Currently Used APIs

These are the methods wired to existing MCP tools:

| API Call | Used By Tool | Notes |
|---|---|---|
| `client.accounts.getAll()` | `get_accounts` | Returns `Account[]`. Pass `{includeHidden: true}` for hidden accounts. |
| `client.accounts.getHistory(id, start?, end?)` | `get_account_history` | Returns `AccountBalance[]`. |
| `client.accounts.getNetWorthHistory()` | `get_financial_health_score` | Returns `{date, netWorth}[]`. |
| `client.transactions.getTransactions(opts)` | `get_transactions`, `search_transactions`, analysis tools | Returns `PaginatedTransactions` — **access `.transactions` for the array**. Use `categoryIds` (plural, array) not `categoryId`. |
| `client.budgets.getBudgets(opts)` | `get_budgets` | Returns `BudgetData` — access `.budgetData.monthlyAmountsByCategory` for budget items. |
| `client.budgets.getCashFlow(opts)` | `get_cashflow` | Returns detailed category-level income/expense data. |
| `client.budgets.getCashFlowSummary(opts)` | `get_cashflow_summary` | Returns aggregated totals. |
| `client.recurring.getRecurringStreams()` | `get_recurring_transactions` | Returns `{stream: RecurringTransactionStream}[]`. Access `r.stream.id`, `r.stream.merchant.name`, `r.stream.amount`, `r.stream.frequency`, `r.stream.baseDate`. |
| `client.categories.getCategories()` | `get_categories` | Returns `TransactionCategory[]`. |
| `client.categories.getCategoryGroups()` | `get_category_groups` | Returns `CategoryGroup[]`. |
| `client.institutions.getInstitutions()` | `get_institutions` | Returns `Institution[]`. |
| `client.insights.getNetWorthHistory(opts)` | `get_net_worth`, `get_net_worth_history` | Returns net worth time series. |

### Unused APIs (Available for New Tools)

These methods exist in the `monarchmoney` npm package but are **not yet wired** as MCP tools. These are candidates for expansion:

**Transaction CRUD:**
- `client.transactions.createTransaction(data)` — Create a manual transaction
- `client.transactions.updateTransaction(id, data)` — Update an existing transaction
- `client.transactions.deleteTransaction(id)` — Delete a transaction
- `client.transactions.getTransactionDetails(id)` — Full details for a single transaction
- `client.transactions.bulkUpdateTransactions(data)` — Bulk update transactions

**Transaction Rules:**
- `client.transactions.getTransactionRules()` — Get auto-categorization rules
- `client.transactions.createTransactionRule(data)` — Create a rule
- `client.transactions.updateTransactionRule(id, data)` — Update a rule
- `client.transactions.deleteTransactionRule(id)` — Delete a rule

**Tags:**
- `client.categories.getTags()` — Get all transaction tags
- `client.categories.createTag(data)` — Create a tag
- `client.categories.setTransactionTags(txId, tagIds)` — Tag a transaction

**Goals:**
- `client.budgets.getGoals()` — Get financial goals
- `client.budgets.createGoal(params)` — Create a goal
- `client.budgets.updateGoal(id, updates)` — Update a goal

**Account Management:**
- `client.accounts.createManualAccount(input)` — Create a manual account
- `client.accounts.updateAccount(id, updates)` — Update account settings
- `client.accounts.requestRefresh(accountIds?)` — Force account sync
- `client.accounts.getBalances(start?, end?)` — Get balance history

**Merchants:**
- `client.transactions.getMerchants(opts)` — Get merchant list
- `client.transactions.getMerchantDetails(id)` — Get merchant details

**Insights:**
- `client.insights.getCreditScore()` — Credit score and history
- `client.insights.getInsights()` — Financial insights/tips
- `client.insights.getSubscriptionDetails()` — Subscription analysis
- `client.insights.getNotifications()` — User notifications

**Advanced Recurring:**
- `client.recurring.getUpcomingRecurringItems(opts)` — Upcoming bills
- `client.recurring.markStreamAsNotRecurring(streamId)` — Dismiss a recurring stream

**Exploring the SDK further:** Check `node_modules/monarchmoney/dist/types/` for all type definitions and `node_modules/monarchmoney/dist/api/` for method implementations.

### Common Type Gotchas

| Gotcha | Correct Usage |
|---|---|
| `getTransactions()` returns a wrapper | Access `.transactions` for the array: `result.transactions` |
| Transaction category can be null | Always use `tx.category?.name ?? "Uncategorized"` |
| Account `.type` is an object | It's `{id, name, display}`, not a string. Use `a.type.name` |
| `categoryId` doesn't exist | Use `categoryIds: string[]` (plural, array) |
| `getBudgets()` returns nested data | Access `.budgetData.monthlyAmountsByCategory` for items |
| Recurring stream structure | Each item is `{stream: RecurringTransactionStream}`, access via `r.stream.*` |
| `getRecurringStreams()` vs `getRecurringTransactions()` | Use `getRecurringStreams()` — the other is on `client.transactions` and returns a different shape |

### Data Flow Pattern

```
Tool Handler (src/tools/*.ts)
  │
  ├── Fetches data:  client = await getMonarchClient()
  │                  data = await client.someApi.someMethod()
  │
  ├── (optional) Transforms data for analysis function
  │
  ├── (optional) Calls pure analysis:  result = analyzeSpending(data, options)
  │
  └── Returns:  { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] }
```

---

## Deployment — Fly.io

This project is configured for Fly.io deployment. Key files:

- **`fly.toml`** — App config: `monarch-money-mcp`, region `sjc`, port 3200, persistent volume at `/data`
- **`Dockerfile`** — `oven/bun:1` base, non-root user, production deps only

**Live deployment:** https://monarch-money-mcp.fly.dev/

### CI/CD

- **CI** (`.github/workflows/ci.yml`): Runs `tsc --noEmit` and `bun test` on every push and PR to `master`
- **Deploy** (`.github/workflows/deploy.yml`): Auto-deploys to Fly.io on every push to `master`
- **Required secret**: `FLY_API_TOKEN` — set in GitHub repo Settings → Secrets → Actions

### Fly.io Commands

```bash
# First-time setup
fly launch                           # Create the app on Fly
fly volumes create mcp_data --size 1 # Create 1GB persistent volume for SQLite

# Set secrets (NEVER commit these)
fly secrets set \
  MONARCH_EMAIL="..." \
  MONARCH_PASSWORD="..." \
  MONARCH_MFA_SECRET="..."

# Deploy
fly deploy

# Check status
fly status
fly logs

# SSH into the running machine
fly ssh console

# Scale
fly scale count 1                    # Single instance (SQLite requires it)
fly scale memory 512                 # Increase memory if needed

# Database access
fly ssh console -C "ls -la /data/"   # Check SQLite files on the volume
```

### Fly.io Architecture

```
Internet → Fly Proxy (HTTPS, auto-TLS)
  → monarch-money-mcp container (Bun, port 3200)
    → /data/monarch-mcp.db (SQLite on persistent volume)
    → Monarch Money API (outbound HTTPS)
```

- **Single instance required** — SQLite doesn't support multi-writer. `fly.toml` sets `min_machines_running = 0` with auto-stop/start.
- **Persistent volume** — SQLite DB lives at `/data/monarch-mcp.db`. Set `DB_PATH=/data/monarch-mcp.db` in env.
- **Auto-stop** — Machine stops after idle period, restarts on incoming request (~2-3s cold start with Bun).
- **Secrets** — Injected as env vars at runtime. View with `fly secrets list`, never logged.

### Fly.io Troubleshooting

| Issue | Fix |
|---|---|
| "No machines running" | `fly machines start` or wait for auto-start on next request |
| SQLite "database is locked" | Ensure only 1 machine: `fly scale count 1` |
| Volume not found | `fly volumes list` — create if missing |
| Out of memory | `fly scale memory 512` |
| Cold start too slow | Set `min_machines_running = 1` in `fly.toml` (costs more) |
| Health check failing | Check `/health` endpoint, verify `PORT=3200`, check `fly logs` |

---

## Deployment — Docker (Generic)

```bash
docker build -t monarch-money-mcp .

docker run -d \
  --name monarch-mcp \
  -p 3200:3200 \
  -v monarch-data:/data \
  -e MONARCH_EMAIL="..." \
  -e MONARCH_PASSWORD="..." \
  -e MONARCH_MFA_SECRET="..." \
  -e DB_PATH=/data/monarch-mcp.db \
  -e TRANSPORT=http \
  monarch-money-mcp

# Verify
curl http://localhost:3200/health
```

---

## HTTP Endpoints (HTTP mode only)

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | None | Health check |
| `POST` | `/mcp` | None* | MCP JSON-RPC endpoint (Streamable HTTP) |
| `GET` | `/.well-known/oauth-authorization-server` | None | RFC 8414 OAuth metadata |
| `POST` | `/oauth/register` | None | RFC 7591 dynamic client registration |
| `GET` | `/oauth/authorize` | None | OAuth authorization form (HTML) |
| `POST` | `/oauth/authorize` | None | Process authorization, redirect with code |
| `POST` | `/oauth/token` | None | Token exchange (authorization_code, refresh_token) |
| `GET` | `/api/v1/health` | None | REST API health check |

*MCP endpoint uses session-based auth via `Mcp-Session-Id` header.

---

## OAuth 2.1 Flow (for Claude Custom Connectors)

```
1. Client → POST /oauth/register         → { client_id }
2. Client → GET /oauth/authorize?...      → HTML login form
3. User submits credentials               → validates against Monarch Money API
4. Server → redirect to redirect_uri?code=...&state=...
5. Client → POST /oauth/token             → { access_token, refresh_token }
6. Client → POST /mcp (with Bearer token) → MCP tool calls
```

PKCE (S256) is enforced. Auth codes expire in 10 minutes. Access tokens expire in 1 hour. Refresh tokens last 30 days.

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `MONARCH_EMAIL` | Yes | — | Monarch Money email |
| `MONARCH_PASSWORD` | Yes | — | Monarch Money password |
| `MONARCH_MFA_SECRET` | No | — | TOTP secret for MFA |
| `PORT` | No | `3200` | HTTP server port |
| `TRANSPORT` | No | `stdio` | `stdio` or `http` (CLI `--transport` overrides) |
| `DB_PATH` | No | `monarch-mcp.db` | SQLite database path |
| `OAUTH_CLIENT_ID` | No | — | Pre-registered OAuth client ID |
| `OAUTH_CLIENT_SECRET` | No | — | OAuth client secret |
| `CORS_ORIGINS` | No | `https://claude.ai,...` | Comma-separated CORS origins |
| `RATE_LIMIT_RPM` | No | `60` | Requests per minute per IP |
| `LOG_LEVEL` | No | `info` | Logging level |

---

## Conventions

- **Tool handlers** always return `{ content: [{ type: "text", text: ... }] }`. On error: `isError: true`.
- **Date params** are `"YYYY-MM-DD"` strings, always optional with sensible defaults.
- **Analysis functions** are pure — no API calls, no side effects. Makes them trivial to unit test.
- **All API calls** go through `getMonarchClient()` — never instantiate `MonarchClient` directly.
- **Error handling** — wrap every tool handler in try/catch, return the error message to the AI rather than throwing.
- **Type-check before committing** — `bun check-types` must pass with zero errors.
- **No secrets in code** — credentials come from env vars only. `.env` is gitignored.
- **Use non-deprecated APIs** — `server.registerTool()`, `server.registerResource()`, `server.registerPrompt()`, `db.run()`.

---

## Testing

```bash
bun test                              # All tests (68 tests, 7 files)
bun test src/analysis/                # Analysis unit tests only
bun test src/oauth/                   # OAuth store tests only
HAS_REAL_CREDENTIALS=true bun test    # Include integration tests (needs real Monarch creds)
```

Test files live alongside source as `*.test.ts` files:
- `src/analysis/spending.test.ts` — spending breakdowns, categories, daily averages, prior period comparison
- `src/analysis/anomalies.test.ts` — unusual amounts, duplicates, new merchant detection
- `src/analysis/trends.test.ts` — increasing/decreasing/stable trend detection
- `src/analysis/forecasting.test.ts` — balance projection, confidence bounds, account filtering
- `src/analysis/subscriptions.test.ts` — merchant grouping, frequency detection, price changes
- `src/analysis/health.test.ts` — composite scoring, 5 components, recommendations
- `src/oauth/store.test.ts` — client registration, auth codes, token lifecycle, refresh rotation

Analysis functions can be tested with mock data — no API mocking needed. Tool handlers require mocking `getMonarchClient()`.
