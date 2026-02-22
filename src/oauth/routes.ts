import { Hono } from "hono";
import { timingSafeEqual } from "crypto";
import {
  generateAuthCode,
  consumeAuthCode,
  generateTokenPair,
  refreshAccessToken,
  registerClient,
  validateClient,
  getClientRedirectUris,
} from "./store.js";

/** Constant-time string comparison to prevent timing attacks */
function safeCompare(a: string, b: string): boolean {
  const bufA = Buffer.from(a);
  const bufB = Buffer.from(b);
  if (bufA.length !== bufB.length) {
    // Compare against self to keep constant time, then return false
    timingSafeEqual(bufA, bufA);
    return false;
  }
  return timingSafeEqual(bufA, bufB);
}

export const oauthRouter = new Hono();

// ── Helper: PKCE S256 verification ──────────────────────────────────────────

async function verifyCodeChallenge(
  codeVerifier: string,
  codeChallenge: string
): Promise<boolean> {
  const encoder = new TextEncoder();
  const data = encoder.encode(codeVerifier);
  const digest = await crypto.subtle.digest("SHA-256", data);
  const base64url = btoa(String.fromCharCode(...new Uint8Array(digest)))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
  return base64url === codeChallenge;
}

// ── RFC 8414: OAuth Authorization Server Metadata ───────────────────────────

oauthRouter.get("/.well-known/oauth-authorization-server", (c) => {
  const url = new URL(c.req.url);
  const proto = c.req.header("x-forwarded-proto") || url.protocol.replace(":", "");
  const issuer = `${proto}://${url.host}`;

  return c.json({
    issuer,
    authorization_endpoint: `${issuer}/oauth/authorize`,
    token_endpoint: `${issuer}/oauth/token`,
    registration_endpoint: `${issuer}/oauth/register`,
    response_types_supported: ["code"],
    grant_types_supported: ["authorization_code", "refresh_token"],
    token_endpoint_auth_methods_supported: ["none"],
    code_challenge_methods_supported: ["S256"],
    scopes_supported: ["monarch:read", "monarch:write"],
  });
});

// ── RFC 7591: Dynamic Client Registration ───────────────────────────────────

oauthRouter.post("/oauth/register", async (c) => {
  let body: Record<string, unknown>;
  try {
    body = await c.req.json();
  } catch {
    return c.json(
      { error: "invalid_request", error_description: "Invalid JSON body." },
      400
    );
  }

  const clientName = (body.client_name as string) || "Unknown Client";
  const redirectUris = body.redirect_uris as string[] | undefined;

  if (
    !redirectUris ||
    !Array.isArray(redirectUris) ||
    redirectUris.length === 0
  ) {
    return c.json(
      {
        error: "invalid_client_metadata",
        error_description: "redirect_uris must be a non-empty array of URIs.",
      },
      400
    );
  }

  // Validate each redirect URI
  for (const uri of redirectUris) {
    try {
      new URL(uri);
    } catch {
      return c.json(
        {
          error: "invalid_client_metadata",
          error_description: `Invalid redirect URI: ${uri}`,
        },
        400
      );
    }
  }

  const { clientId } = registerClient(clientName, redirectUris);

  return c.json(
    {
      client_id: clientId,
      client_name: clientName,
      redirect_uris: redirectUris,
      token_endpoint_auth_method: "none",
      grant_types: ["authorization_code", "refresh_token"],
      response_types: ["code"],
    },
    201
  );
});

// ── GET /oauth/authorize — Show authorization form ──────────────────────────

oauthRouter.get("/oauth/authorize", (c) => {
  const clientId = c.req.query("client_id");
  const redirectUri = c.req.query("redirect_uri");
  const state = c.req.query("state") || "";
  const codeChallenge = c.req.query("code_challenge") || "";
  const codeChallengeMethod = c.req.query("code_challenge_method") || "";
  const responseType = c.req.query("response_type");

  if (responseType !== "code") {
    return c.json(
      {
        error: "unsupported_response_type",
        error_description: "Only response_type=code is supported.",
      },
      400
    );
  }

  if (!clientId || !redirectUri) {
    return c.json(
      {
        error: "invalid_request",
        error_description: "client_id and redirect_uri are required.",
      },
      400
    );
  }

  if (!validateClient(clientId)) {
    return c.json(
      {
        error: "invalid_client",
        error_description: "Unknown client_id.",
      },
      400
    );
  }

  // Validate redirect_uri against registered URIs
  const registeredUris = getClientRedirectUris(clientId);
  if (!registeredUris.includes(redirectUri)) {
    return c.json(
      {
        error: "invalid_request",
        error_description: "redirect_uri does not match any registered URIs.",
      },
      400
    );
  }

  const html = renderAuthForm({
    clientId,
    redirectUri,
    state,
    codeChallenge,
    codeChallengeMethod,
  });

  return c.html(html);
});

// ── POST /oauth/authorize — Validate passphrase, redirect with code ─────────

oauthRouter.post("/oauth/authorize", async (c) => {
  let body: Record<string, string>;
  try {
    const formData = await c.req.formData();
    body = Object.fromEntries(formData.entries()) as Record<string, string>;
  } catch {
    return c.json(
      { error: "invalid_request", error_description: "Invalid form data." },
      400
    );
  }

  const {
    passphrase,
    client_id: clientId,
    redirect_uri: redirectUri,
    state,
    code_challenge: codeChallenge,
    code_challenge_method: codeChallengeMethod,
  } = body;

  if (!passphrase) {
    return c.html(
      renderAuthForm({
        clientId: clientId || "",
        redirectUri: redirectUri || "",
        state: state || "",
        codeChallenge: codeChallenge || "",
        codeChallengeMethod: codeChallengeMethod || "",
        errorMessage: "Passphrase is required.",
      }),
      400
    );
  }

  if (!clientId || !redirectUri) {
    return c.json(
      {
        error: "invalid_request",
        error_description: "client_id and redirect_uri are required.",
      },
      400
    );
  }

  if (!validateClient(clientId)) {
    return c.json(
      { error: "invalid_client", error_description: "Unknown client_id." },
      400
    );
  }

  // Validate redirect_uri
  const registeredUris = getClientRedirectUris(clientId);
  if (!registeredUris.includes(redirectUri)) {
    return c.json(
      {
        error: "invalid_request",
        error_description: "redirect_uri does not match any registered URIs.",
      },
      400
    );
  }

  // Validate passphrase against server secret
  const expectedPassphrase = process.env.OAUTH_PASSPHRASE;
  if (!expectedPassphrase) {
    return c.html(
      renderAuthForm({
        clientId,
        redirectUri,
        state: state || "",
        codeChallenge: codeChallenge || "",
        codeChallengeMethod: codeChallengeMethod || "",
        errorMessage: "Server misconfigured: OAUTH_PASSPHRASE not set.",
      }),
      500
    );
  }

  if (!safeCompare(passphrase, expectedPassphrase)) {
    return c.html(
      renderAuthForm({
        clientId,
        redirectUri,
        state: state || "",
        codeChallenge: codeChallenge || "",
        codeChallengeMethod: codeChallengeMethod || "",
        errorMessage: "Invalid passphrase.",
      }),
      401
    );
  }

  // Issue authorization code
  const code = generateAuthCode(
    clientId,
    redirectUri,
    codeChallenge || undefined,
    codeChallengeMethod || undefined
  );

  // Build redirect URL
  const redirect = new URL(redirectUri);
  redirect.searchParams.set("code", code);
  if (state) {
    redirect.searchParams.set("state", state);
  }

  return c.redirect(redirect.toString(), 302);
});

// ── POST /oauth/token — Exchange code for tokens ────────────────────────────

oauthRouter.post("/oauth/token", async (c) => {
  let body: Record<string, string>;
  try {
    // Support both form-encoded and JSON bodies
    const contentType = c.req.header("content-type") || "";
    if (contentType.includes("application/json")) {
      body = await c.req.json();
    } else {
      const formData = await c.req.formData();
      body = Object.fromEntries(formData.entries()) as Record<string, string>;
    }
  } catch {
    return c.json(
      { error: "invalid_request", error_description: "Invalid request body." },
      400
    );
  }

  const grantType = body.grant_type;

  // ── authorization_code grant ────────────────────────────────────────────

  if (grantType === "authorization_code") {
    const { code, client_id: clientId, redirect_uri: redirectUri, code_verifier: codeVerifier } = body;

    if (!code || !clientId) {
      return c.json(
        {
          error: "invalid_request",
          error_description: "code and client_id are required.",
        },
        400
      );
    }

    const authCode = consumeAuthCode(code);
    if (!authCode) {
      return c.json(
        {
          error: "invalid_grant",
          error_description: "Authorization code is invalid, expired, or already used.",
        },
        400
      );
    }

    // Verify client_id matches
    if (authCode.client_id !== clientId) {
      return c.json(
        {
          error: "invalid_grant",
          error_description: "client_id does not match the authorization code.",
        },
        400
      );
    }

    // Verify redirect_uri matches
    if (redirectUri && authCode.redirect_uri !== redirectUri) {
      return c.json(
        {
          error: "invalid_grant",
          error_description: "redirect_uri does not match the authorization code.",
        },
        400
      );
    }

    // PKCE verification
    if (authCode.code_challenge && authCode.code_challenge_method === "S256") {
      if (!codeVerifier) {
        return c.json(
          {
            error: "invalid_grant",
            error_description: "code_verifier is required for PKCE.",
          },
          400
        );
      }

      const valid = await verifyCodeChallenge(
        codeVerifier,
        authCode.code_challenge
      );
      if (!valid) {
        return c.json(
          {
            error: "invalid_grant",
            error_description: "PKCE code_verifier verification failed.",
          },
          400
        );
      }
    }

    const tokens = generateTokenPair(clientId);

    return c.json({
      access_token: tokens.accessToken,
      token_type: "Bearer",
      expires_in: tokens.expiresIn,
      refresh_token: tokens.refreshToken,
    });
  }

  // ── refresh_token grant ─────────────────────────────────────────────────

  if (grantType === "refresh_token") {
    const { refresh_token: refreshToken, client_id: clientId } = body;

    if (!refreshToken) {
      return c.json(
        {
          error: "invalid_request",
          error_description: "refresh_token is required.",
        },
        400
      );
    }

    const tokens = refreshAccessToken(refreshToken);
    if (!tokens) {
      return c.json(
        {
          error: "invalid_grant",
          error_description: "Refresh token is invalid or expired.",
        },
        400
      );
    }

    return c.json({
      access_token: tokens.accessToken,
      token_type: "Bearer",
      expires_in: tokens.expiresIn,
      refresh_token: tokens.refreshToken,
    });
  }

  // ── Unsupported grant type ──────────────────────────────────────────────

  return c.json(
    {
      error: "unsupported_grant_type",
      error_description: `Grant type "${grantType}" is not supported. Use "authorization_code" or "refresh_token".`,
    },
    400
  );
});

// ── HTML Auth Form ──────────────────────────────────────────────────────────

function renderAuthForm(params: {
  clientId: string;
  redirectUri: string;
  state: string;
  codeChallenge: string;
  codeChallengeMethod: string;
  errorMessage?: string;
}): string {
  const errorHtml = params.errorMessage
    ? `<div class="error">${escapeHtml(params.errorMessage)}</div>`
    : "";

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Monarch Money MCP - Authorize</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #0f0f13;
      color: #e4e4e7;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      padding: 1rem;
    }
    .card {
      background: #1a1a23;
      border: 1px solid #2a2a35;
      border-radius: 16px;
      box-shadow: 0 4px 24px rgba(0,0,0,0.3);
      padding: 2.5rem 2rem;
      width: 100%;
      max-width: 420px;
    }
    .logo {
      text-align: center;
      margin-bottom: 2rem;
    }
    .logo h1 {
      font-size: 1.35rem;
      font-weight: 600;
      color: #f4f4f5;
      letter-spacing: -0.01em;
    }
    .logo p {
      font-size: 0.85rem;
      color: #71717a;
      margin-top: 0.5rem;
    }
    .error {
      background: rgba(220, 38, 38, 0.1);
      border: 1px solid rgba(220, 38, 38, 0.3);
      color: #fca5a5;
      padding: 0.75rem 1rem;
      border-radius: 8px;
      font-size: 0.875rem;
      margin-bottom: 1.25rem;
    }
    label {
      display: block;
      font-size: 0.875rem;
      font-weight: 500;
      margin-bottom: 0.4rem;
      color: #a1a1aa;
    }
    input[type="password"] {
      width: 100%;
      padding: 0.7rem 0.85rem;
      background: #0f0f13;
      border: 1px solid #2a2a35;
      border-radius: 8px;
      font-size: 0.9375rem;
      color: #e4e4e7;
      margin-bottom: 1.25rem;
      transition: border-color 0.15s;
    }
    input:focus {
      outline: none;
      border-color: #6366f1;
      box-shadow: 0 0 0 3px rgba(99,102,241,0.15);
    }
    input::placeholder { color: #52525b; }
    button {
      width: 100%;
      padding: 0.75rem;
      background: #6366f1;
      color: #fff;
      border: none;
      border-radius: 8px;
      font-size: 1rem;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.15s;
    }
    button:hover { background: #4f46e5; }
    button:active { background: #4338ca; }
    .help {
      margin-top: 1.5rem;
      text-align: center;
      font-size: 0.8rem;
      color: #52525b;
      line-height: 1.5;
    }
    .help a {
      color: #818cf8;
      text-decoration: none;
    }
    .help a:hover { text-decoration: underline; }
  </style>
</head>
<body>
  <div class="card">
    <div class="logo">
      <h1>Monarch Money MCP</h1>
      <p>Enter your server passphrase to authorize access</p>
    </div>
    ${errorHtml}
    <form method="POST" action="/oauth/authorize">
      <input type="hidden" name="client_id" value="${escapeAttr(params.clientId)}" />
      <input type="hidden" name="redirect_uri" value="${escapeAttr(params.redirectUri)}" />
      <input type="hidden" name="state" value="${escapeAttr(params.state)}" />
      <input type="hidden" name="code_challenge" value="${escapeAttr(params.codeChallenge)}" />
      <input type="hidden" name="code_challenge_method" value="${escapeAttr(params.codeChallengeMethod)}" />

      <label for="passphrase">Passphrase</label>
      <input type="password" id="passphrase" name="passphrase" required autocomplete="off" placeholder="Enter server passphrase" />

      <button type="submit">Authorize</button>
    </form>
    <p class="help">
      Need help configuring? <a href="https://www.cesarbenavides.com/" target="_blank" rel="noopener">Contact me here</a>
    </p>
  </div>
</body>
</html>`;
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function escapeAttr(str: string): string {
  return str
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}
