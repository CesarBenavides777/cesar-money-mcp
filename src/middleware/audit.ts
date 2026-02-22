import type { MiddlewareHandler } from "hono";

/**
 * Structured audit logging middleware.
 *
 * Emits one JSON log line per request with timing, status, method, path,
 * and client IP. Logs are written to stdout for easy ingestion by external
 * log aggregators (Fly.io, Datadog, etc.).
 */
export function auditLog(): MiddlewareHandler {
  return async (c, next) => {
    const start = Date.now();
    const method = c.req.method;
    const path = c.req.path;
    const ip =
      c.req.header("x-forwarded-for")?.split(",")[0]?.trim() ||
      c.req.header("x-real-ip") ||
      "unknown";
    const userAgent = c.req.header("user-agent") || "unknown";

    await next();

    const duration = Date.now() - start;
    const status = c.res.status;

    console.log(
      JSON.stringify({
        timestamp: new Date().toISOString(),
        level: status >= 500 ? "error" : status >= 400 ? "warn" : "info",
        method,
        path,
        status,
        duration,
        ip,
        userAgent,
      })
    );
  };
}
