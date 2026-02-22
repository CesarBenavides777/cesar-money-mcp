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
| `bun test` | Run test suite |

---

## Key Skills for Agents

### 1. Adding a New MCP Tool

Create or edit a file in `src/tools/`. Each file exports a `registerXxxTools(server)` function:

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { getMonarchClient } from "../monarch/client.js";

export function registerMyTools(server: McpServer) {
  server.tool(
    "tool_name",
    "Clear description of what this tool does and when to use it.",
    {
      param_name: z.string().optional().describe("What this parameter controls."),
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

### 3. Using the Monarch Money Client

```typescript
import { getMonarchClient } from "../monarch/client.js";

const client = await getMonarchClient(); // Singleton, auto-login, session-cached

// Sub-APIs:
client.accounts.getAll()
client.accounts.getHistory(accountId, startDate?, endDate?)
client.accounts.getNetWorthHistory(startDate?, endDate?)
client.transactions.getTransactions({ limit?, offset?, startDate?, endDate?, search?, categoryIds?, accountIds? })
client.transactions.getTransactionDetails(id)
client.transactions.getRecurringTransactions()
client.transactions.getTransactionCategories()
client.transactions.getTransactionCategoryGroups()
client.budgets.getBudgets({ startDate?, endDate? })
client.budgets.getCashFlow({ startDate?, endDate? })
client.budgets.getCashFlowSummary({ startDate?, endDate? })
client.categories.getCategories()
client.categories.getCategoryGroups()
client.institutions.getInstitutions()
client.insights.getNetWorthHistory({ startDate?, endDate? })
client.insights.getSubscriptionDetails()
client.recurring.getRecurringStreams()
```

**Important:** `getTransactions()` returns `PaginatedTransactions` — access `.transactions` for the array. Use `categoryIds` (plural, array) not `categoryId`.

### 4. Adding an MCP Resource

In `src/tools/resources.ts`:

```typescript
server.resource("name", "finance://uri", async (uri) => {
  const client = await getMonarchClient();
  const data = await client.someApi.someMethod();
  return { contents: [{ uri: uri.href, mimeType: "application/json", text: JSON.stringify(data, null, 2) }] };
});
```

### 5. Adding an MCP Prompt

In `src/tools/prompts.ts`:

```typescript
server.prompt("prompt-name", "Description", {}, async () => ({
  messages: [{ role: "user" as const, content: { type: "text" as const, text: "Instructions for the AI..." } }],
}));
```

---

## Deployment — Fly.io

This project is configured for Fly.io deployment. Key files:

- **`fly.toml`** — App config: `monarch-money-mcp`, region `sjc`, port 3200, persistent volume at `/data`
- **`Dockerfile`** — `oven/bun:1` base, non-root user, production deps only

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

---

## Testing

```bash
bun test                              # All tests
bun test src/analysis/                # Analysis unit tests only
HAS_REAL_CREDENTIALS=true bun test    # Include integration tests (needs real Monarch creds)
```

Analysis functions can be tested with mock data — no API mocking needed. Tool handlers require mocking `getMonarchClient()`.
