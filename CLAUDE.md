# Monarch Money MCP Server

## Project Overview

TypeScript MCP server for Monarch Money personal finance data. Provides 20+ tools, MCP resources, and canned prompts for AI assistants to query accounts, transactions, budgets, cash flow, net worth, and more. Includes an analysis engine for spending breakdowns, anomaly detection, cash flow forecasting, subscription tracking, trend detection, and financial health scoring.

Supports two transports:
- **stdio** -- for Claude Desktop and Claude Code
- **HTTP** (Streamable HTTP via Hono) -- for Claude Custom Connectors and remote clients, with full OAuth 2.1 + PKCE

## Tech Stack

- **Runtime**: Bun (>= 1.0)
- **HTTP Framework**: Hono
- **MCP**: `@modelcontextprotocol/sdk` (^1.12.0)
- **Finance API**: `monarchmoney` npm package (^1.1.3)
- **Auth**: OAuth 2.1 with PKCE, SQLite token storage via `bun:sqlite`
- **Validation**: Zod
- **TypeScript**: ^5.7, target ES2022, module ESNext, bundler resolution

## Project Structure

```
src/
├── index.ts                  # Entry point: picks stdio or HTTP mode, bootstraps the app
├── config.ts                 # Loads env vars + CLI flags into a typed Config object
├── monarch/
│   └── client.ts             # Singleton MonarchClient with login, session caching, retry, and response caching
├── mcp/
│   ├── server.ts             # Creates McpServer and registers all tools, resources, and prompts
│   └── transport.ts          # HttpTransport: bridges Hono HTTP requests to MCP's Transport interface
├── tools/
│   ├── index.ts              # Barrel re-exports for all tool registration functions
│   ├── accounts.ts           # get_accounts, get_account_history
│   ├── transactions.ts       # get_transactions, search_transactions
│   ├── budgets.ts            # get_budgets
│   ├── cashflow.ts           # get_cashflow, get_cashflow_summary
│   ├── recurring.ts          # get_recurring_transactions
│   ├── categories.ts         # get_categories, get_category_groups
│   ├── institutions.ts       # get_institutions
│   ├── insights.ts           # get_net_worth, get_net_worth_history
│   ├── analysis.ts           # Wrappers that call analysis/ functions and expose them as MCP tools
│   ├── resources.ts          # MCP resource definitions (finance:// URIs)
│   └── prompts.ts            # MCP prompt templates (monthly-review, budget-check, etc.)
├── analysis/
│   ├── index.ts              # Barrel exports for all analysis functions and types
│   ├── spending.ts           # analyzeSpending — category breakdowns, top merchants, daily averages
│   ├── anomalies.ts          # detectAnomalies — large purchases, duplicates, unfamiliar merchants
│   ├── forecasting.ts        # forecastCashflow — 30/60/90-day balance projections
│   ├── subscriptions.ts      # analyzeSubscriptions — recurring payment analysis, price changes
│   ├── trends.ts             # detectTrends — multi-month category spending direction
│   └── health.ts             # calculateHealthScore — composite 0-100 financial health score
├── oauth/
│   ├── routes.ts             # Hono routes: .well-known, /oauth/register, /oauth/authorize, /oauth/token
│   ├── provider.ts           # validateMonarchCredentials — login-to-verify (no storage)
│   └── store.ts              # SQLite-backed store for auth codes, tokens, and dynamic clients
└── middleware/
    ├── auth.ts               # bearerAuth() — validates access tokens from Authorization header
    ├── rate-limit.ts         # rateLimit() — per-IP sliding window, returns 429 when exceeded
    └── audit.ts              # auditLog() — structured JSON log line per request with timing
```

## Key Patterns

### Adding a New Data Tool

1. Create or edit a file in `src/tools/` (e.g., `src/tools/my-feature.ts`)
2. Export a `registerMyFeatureTools(server: McpServer)` function
3. Import and call it in `src/mcp/server.ts`
4. Follow this pattern:

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { getMonarchClient } from "../monarch/client.js";

export function registerMyFeatureTools(server: McpServer) {
  server.tool(
    "my_tool_name",
    "Description of what this tool does and when the AI should use it.",
    {
      // Zod schema for parameters
      someParam: z.string().optional().describe("What this parameter does."),
    },
    async ({ someParam }) => {
      try {
        const client = await getMonarchClient();
        const data = await client.someApi.someMethod({ someParam });
        return {
          content: [
            { type: "text" as const, text: JSON.stringify(data, null, 2) },
          ],
        };
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        return {
          content: [{ type: "text" as const, text: `Error: ${message}` }],
          isError: true,
        };
      }
    }
  );
}
```

### Adding an Analysis Function

1. Create a pure function in `src/analysis/` (no MCP or API dependencies)
2. Export types and the function from `src/analysis/index.ts`
3. Wire it up as a tool in `src/tools/analysis.ts` by:
   - Importing the analysis function
   - Fetching required data via `getMonarchClient()`
   - Passing the data to the pure function
   - Returning the result as JSON text content

Analysis functions should be pure (data in, result out) so they are easy to unit test without mocking the Monarch API.

### Monarch Client Usage

- Always use `getMonarchClient()` from `src/monarch/client.ts`
- It is a singleton that handles login, session caching, and auto-revalidation
- If the session expires, it automatically re-authenticates
- The client is configured with 30s timeout, 3 retries, and a 5-minute response cache
- API sub-domains: `client.accounts`, `client.transactions`, `client.budgets`, `client.categories`, `client.institutions`, `client.insights`, `client.recurring`
- Use `resetMonarchClient()` to force a fresh login (e.g., after credential changes)

### Adding an MCP Resource

Register in `src/tools/resources.ts`:

```typescript
server.resource(
  "resource-name",      // Human-readable name
  "finance://my-uri",   // URI
  async (uri) => {
    const client = await getMonarchClient();
    const data = await client.someApi.someMethod();
    return {
      contents: [{
        uri: uri.href,
        mimeType: "application/json",
        text: JSON.stringify(data, null, 2),
      }],
    };
  }
);
```

### Adding an MCP Prompt

Register in `src/tools/prompts.ts`:

```typescript
server.prompt(
  "prompt-name",
  "Description of the analysis this prompt performs",
  {},
  async () => ({
    messages: [{
      role: "user" as const,
      content: {
        type: "text" as const,
        text: "Detailed instructions for the AI, including which tools to call and how to format the report...",
      },
    }],
  })
);
```

## Commands

| Command | Description |
|---|---|
| `bun dev` | Watch mode (auto-restart on file changes) |
| `bun start` | Start with default transport (stdio) |
| `bun start:stdio` | Start in stdio transport mode |
| `bun start:http` | Start HTTP server on port 3200 |
| `bun check-types` | TypeScript type checking (`tsc --noEmit`) |
| `bun test` | Run test suite |
| `bun lint` | Lint source with Biome |
| `bun format` | Auto-format source with Biome |

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `MONARCH_EMAIL` | Yes | -- | Monarch Money account email |
| `MONARCH_PASSWORD` | Yes | -- | Monarch Money account password |
| `MONARCH_MFA_SECRET` | No | -- | TOTP secret for accounts with MFA enabled |
| `PORT` | No | `3200` | HTTP server port |
| `TRANSPORT` | No | `stdio` | Transport mode: `stdio` or `http` (CLI flag `--transport` overrides) |
| `OAUTH_CLIENT_ID` | No | -- | Pre-registered OAuth client ID (HTTP mode) |
| `OAUTH_CLIENT_SECRET` | No | -- | OAuth client secret (HTTP mode) |
| `CORS_ORIGINS` | No | `https://claude.ai,...` | Comma-separated allowed origins for CORS |
| `RATE_LIMIT_RPM` | No | `60` | Max requests per minute per IP |
| `LOG_LEVEL` | No | `info` | Logging level |
| `DB_PATH` | No | `monarch-mcp.db` | Path to SQLite database for OAuth token storage |

## Testing

- `bun test` runs the test suite (unit tests in `tests/unit/`, integration in `tests/integration/`, e2e in `tests/e2e/`)
- Analysis functions in `src/analysis/` are pure and can be tested by passing mock data directly
- For integration tests that hit the real Monarch API, set `HAS_REAL_CREDENTIALS=true` and provide `MONARCH_EMAIL` / `MONARCH_PASSWORD` / `MONARCH_MFA_SECRET`
- Test fixtures live in `tests/fixtures/`

## HTTP Endpoints (HTTP mode only)

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check, returns server status and version |
| `POST` | `/mcp` | Streamable HTTP MCP endpoint (JSON-RPC) |
| `GET` | `/.well-known/oauth-authorization-server` | RFC 8414 OAuth metadata |
| `POST` | `/oauth/register` | RFC 7591 dynamic client registration |
| `GET` | `/oauth/authorize` | OAuth authorization form |
| `POST` | `/oauth/authorize` | Process authorization, redirect with code |
| `POST` | `/oauth/token` | Token exchange (authorization_code, refresh_token) |
| `GET` | `/api/v1/health` | REST API health check |

## Important Notes

- The Monarch Money client uses a cached singleton. If you change credentials at runtime, call `resetMonarchClient()`.
- OAuth tokens are stored in SQLite (default `monarch-mcp.db`). In Docker/Fly.io, mount a persistent volume at `/data` and set `DB_PATH=/data/monarch-mcp.db`.
- All tool handlers return `{ content: [{ type: "text", text: ... }] }`. On error they set `isError: true`.
- The HTTP transport (`src/mcp/transport.ts`) bridges individual HTTP POST requests to the MCP server's async transport interface using a promise-per-request pattern with a 60-second timeout.
- Sessions in HTTP mode are tracked by `Mcp-Session-Id` header and auto-expire after 30 minutes of inactivity.
