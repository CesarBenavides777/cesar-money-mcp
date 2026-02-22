#!/usr/bin/env bun
/**
 * Monarch Money MCP Server
 *
 * Open-source MCP server for personal finance data, analysis, and AI-powered insights.
 * Supports dual transport: stdio (Claude Desktop/Code) and HTTP (Claude Custom Connectors).
 *
 * Usage:
 *   bun src/index.ts --transport stdio   # Local (Claude Desktop/Code)
 *   bun src/index.ts --transport http    # Remote (HTTP server on port 3200)
 */

import { loadConfig } from "./config.js";
import { createMcpServer } from "./mcp/server.js";

const config = loadConfig();

if (config.server.transport === "stdio") {
  await startStdio();
} else {
  startHttp();
}

// ── stdio mode ──────────────────────────────────────────────────────────────

async function startStdio() {
  const { StdioServerTransport } = await import(
    "@modelcontextprotocol/sdk/server/stdio.js"
  );

  const server = createMcpServer();
  const transport = new StdioServerTransport();
  await server.connect(transport);

  process.on("SIGINT", async () => {
    await server.close();
    process.exit(0);
  });
}

// ── HTTP mode ───────────────────────────────────────────────────────────────

function startHttp() {
  const { Hono } = require("hono") as typeof import("hono");
  const { cors } = require("hono/cors") as typeof import("hono/cors");
  const { logger } = require("hono/logger") as typeof import("hono/logger");
  const { HttpTransport } = require("./mcp/transport.js") as typeof import("./mcp/transport.js");
  const { oauthRouter } = require("./oauth/routes.js") as typeof import("./oauth/routes.js");
  const { initTokenStore } = require("./oauth/store.js") as typeof import("./oauth/store.js");
  const { rateLimit } = require("./middleware/rate-limit.js") as typeof import("./middleware/rate-limit.js");
  const { auditLog } = require("./middleware/audit.js") as typeof import("./middleware/audit.js");

  // Initialize token store
  const dbPath = process.env.DB_PATH || "monarch-mcp.db";
  initTokenStore(dbPath);

  const app = new Hono();

  // ── Middleware ──
  app.use(logger());
  app.use(auditLog());
  app.use(
    cors({
      origin: config.server.corsOrigins,
      allowMethods: ["GET", "POST", "OPTIONS"],
      allowHeaders: ["Content-Type", "Authorization", "Mcp-Session-Id"],
      exposeHeaders: [
        "Mcp-Session-Id",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
      ],
    })
  );

  // ── Health check ──
  app.get("/health", (c) =>
    c.json({ status: "ok", server: "monarch-money-mcp", version: "1.0.0" })
  );

  // ── OAuth routes ──
  app.route("/", oauthRouter);

  // ── MCP endpoint (Streamable HTTP) ──
  interface McpSession {
    server: ReturnType<typeof createMcpServer>;
    transport: InstanceType<typeof HttpTransport>;
    lastAccess: number;
  }
  const sessions = new Map<string, McpSession>();

  // Clean up stale sessions every 5 minutes
  setInterval(() => {
    const cutoff = Date.now() - 30 * 60_000;
    for (const [id, session] of sessions) {
      if (session.lastAccess < cutoff) {
        session.transport.close();
        sessions.delete(id);
      }
    }
  }, 5 * 60_000);

  app.post("/mcp", rateLimit({ rpm: config.rateLimit.rpm }), async (c) => {
    const body = await c.req.json();
    const sessionId = c.req.header("mcp-session-id");

    let transport: InstanceType<typeof HttpTransport>;
    let newSessionId: string | undefined;

    if (sessionId && sessions.has(sessionId)) {
      const session = sessions.get(sessionId)!;
      transport = session.transport;
      session.lastAccess = Date.now();
    } else {
      newSessionId = crypto.randomUUID();
      const mcpServer = createMcpServer();
      transport = new HttpTransport();
      await mcpServer.connect(transport);
      sessions.set(newSessionId, {
        server: mcpServer,
        transport,
        lastAccess: Date.now(),
      });
    }

    const response = await transport.handleJsonRpc(body);

    const headers: Record<string, string> = {};
    if (newSessionId) {
      headers["mcp-session-id"] = newSessionId;
    }

    return c.json(response, { headers });
  });

  // ── API routes (REST, for non-MCP consumers) ──
  app.get("/api/v1/health", (c) =>
    c.json({ status: "ok", timestamp: new Date().toISOString() })
  );

  // ── Start server ──
  const port = config.server.port;
  console.log(
    `Monarch Money MCP server listening on http://localhost:${port}`
  );
  console.log(`  MCP endpoint: POST /mcp`);
  console.log(`  Health check: GET /health`);
  console.log(`  OAuth:        GET /.well-known/oauth-authorization-server`);

  Bun.serve({
    port,
    fetch: app.fetch,
  });
}
