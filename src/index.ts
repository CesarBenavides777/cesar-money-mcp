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
  await startHttp();
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

async function startHttp() {
  const { Hono } = await import("hono");
  const { cors } = await import("hono/cors");
  const { logger } = await import("hono/logger");
  const { HttpTransport } = await import("./mcp/transport.js");
  const { oauthRouter } = await import("./oauth/routes.js");
  const { initTokenStore, cleanupExpired } = await import(
    "./oauth/store.js"
  );
  const { rateLimit } = await import("./middleware/rate-limit.js");
  const { auditLog } = await import("./middleware/audit.js");

  // Initialize token store
  initTokenStore(config.dbPath);

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
    c.json({
      status: "ok",
      server: "monarch-money-mcp",
      version: "0.1.0-alpha.1",
    })
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

  // Clean up stale sessions + expired tokens every 5 minutes
  setInterval(() => {
    const cutoff = Date.now() - 30 * 60_000;
    for (const [id, session] of sessions) {
      if (session.lastAccess < cutoff) {
        session.transport.close();
        sessions.delete(id);
      }
    }
    cleanupExpired();
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
