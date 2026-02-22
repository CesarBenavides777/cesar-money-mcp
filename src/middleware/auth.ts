import type { MiddlewareHandler } from "hono";
import { validateAccessToken } from "../oauth/store.js";

/**
 * Bearer token validation middleware.
 *
 * Extracts the token from the Authorization header, validates it against
 * the SQLite token store, and returns 401 on failure.
 */
export function bearerAuth(): MiddlewareHandler {
  return async (c, next) => {
    const auth = c.req.header("Authorization");

    if (!auth?.startsWith("Bearer ")) {
      return c.json(
        {
          error: "unauthorized",
          error_description: "Missing or malformed Authorization header. Expected: Bearer <token>",
        },
        401
      );
    }

    const token = auth.slice(7);

    if (!token) {
      return c.json(
        {
          error: "unauthorized",
          error_description: "Empty bearer token.",
        },
        401
      );
    }

    if (!validateAccessToken(token)) {
      return c.json(
        {
          error: "invalid_token",
          error_description: "The access token is expired or invalid.",
        },
        401
      );
    }

    await next();
  };
}
