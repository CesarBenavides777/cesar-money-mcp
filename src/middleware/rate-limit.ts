import type { MiddlewareHandler } from "hono";

/**
 * Simple per-IP sliding-window rate limiter.
 *
 * Tracks request timestamps in memory and rejects requests that exceed the
 * configured requests-per-minute (rpm) threshold with a 429 status code.
 */
export function rateLimit(
  options: { rpm?: number } = {}
): MiddlewareHandler {
  const limit = options.rpm ?? 60;
  const windowMs = 60_000; // 1 minute sliding window
  const windows = new Map<string, number[]>();

  // Periodic cleanup of stale entries to prevent unbounded memory growth
  const cleanupInterval = setInterval(() => {
    const cutoff = Date.now() - windowMs;
    for (const [ip, timestamps] of windows) {
      const filtered = timestamps.filter((t) => t > cutoff);
      if (filtered.length === 0) {
        windows.delete(ip);
      } else {
        windows.set(ip, filtered);
      }
    }
  }, windowMs);

  // Allow the process to exit cleanly without waiting for the interval
  if (cleanupInterval.unref) {
    cleanupInterval.unref();
  }

  return async (c, next) => {
    const ip =
      c.req.header("x-forwarded-for")?.split(",")[0]?.trim() ||
      c.req.header("x-real-ip") ||
      "unknown";

    const now = Date.now();
    const cutoff = now - windowMs;

    // Get or create the window for this IP
    let timestamps = windows.get(ip);
    if (!timestamps) {
      timestamps = [];
      windows.set(ip, timestamps);
    }

    // Evict expired entries inline for this IP
    const filtered = timestamps.filter((t) => t > cutoff);

    if (filtered.length >= limit) {
      // Calculate when the oldest request in the window will expire
      const oldestInWindow = filtered[0]!;
      const retryAfterSec = Math.ceil((oldestInWindow + windowMs - now) / 1000);

      c.header("Retry-After", String(retryAfterSec));
      c.header("X-RateLimit-Limit", String(limit));
      c.header("X-RateLimit-Remaining", "0");
      c.header("X-RateLimit-Reset", String(Math.ceil((oldestInWindow + windowMs) / 1000)));

      return c.json(
        {
          error: "rate_limit_exceeded",
          error_description: `Too many requests. Limit: ${limit} requests per minute.`,
          retry_after: retryAfterSec,
        },
        429
      );
    }

    // Record this request
    filtered.push(now);
    windows.set(ip, filtered);

    // Set informational rate-limit headers
    c.header("X-RateLimit-Limit", String(limit));
    c.header("X-RateLimit-Remaining", String(limit - filtered.length));

    await next();
  };
}
