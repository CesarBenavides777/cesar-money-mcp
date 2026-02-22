import { Hono } from "hono";
import {
  generateAuthCode,
  consumeAuthCode,
  generateTokenPair,
  refreshAccessToken,
  registerClient,
  validateClient,
  getClientRedirectUris,
} from "./store.js";
import { validateMonarchCredentials } from "./provider.js";

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
  const issuer = new URL(c.req.url).origin;

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

// ── POST /oauth/authorize — Process auth, redirect with code ────────────────

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
    email,
    password,
    mfa_secret: mfaSecret,
    client_id: clientId,
    redirect_uri: redirectUri,
    state,
    code_challenge: codeChallenge,
    code_challenge_method: codeChallengeMethod,
  } = body;

  if (!email || !password) {
    return c.html(
      renderAuthForm({
        clientId: clientId || "",
        redirectUri: redirectUri || "",
        state: state || "",
        codeChallenge: codeChallenge || "",
        codeChallengeMethod: codeChallengeMethod || "",
        errorMessage: "Email and password are required.",
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

  // Authenticate against Monarch Money
  const result = await validateMonarchCredentials(
    email,
    password,
    mfaSecret || undefined
  );

  if (!result.valid) {
    return c.html(
      renderAuthForm({
        clientId,
        redirectUri,
        state: state || "",
        codeChallenge: codeChallenge || "",
        codeChallengeMethod: codeChallengeMethod || "",
        errorMessage: result.error || "Authentication failed.",
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
      background: #f5f5f5;
      color: #333;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      padding: 1rem;
    }
    .card {
      background: #fff;
      border-radius: 12px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.08);
      padding: 2rem;
      width: 100%;
      max-width: 420px;
    }
    .logo {
      text-align: center;
      margin-bottom: 1.5rem;
    }
    .logo h1 {
      font-size: 1.25rem;
      font-weight: 600;
      color: #1a1a2e;
    }
    .logo p {
      font-size: 0.85rem;
      color: #666;
      margin-top: 0.25rem;
    }
    .error {
      background: #fef2f2;
      border: 1px solid #fecaca;
      color: #dc2626;
      padding: 0.75rem 1rem;
      border-radius: 8px;
      font-size: 0.875rem;
      margin-bottom: 1rem;
    }
    label {
      display: block;
      font-size: 0.875rem;
      font-weight: 500;
      margin-bottom: 0.35rem;
      color: #444;
    }
    input[type="email"],
    input[type="password"],
    input[type="text"] {
      width: 100%;
      padding: 0.625rem 0.75rem;
      border: 1px solid #d1d5db;
      border-radius: 8px;
      font-size: 0.9375rem;
      margin-bottom: 1rem;
      transition: border-color 0.15s;
    }
    input:focus {
      outline: none;
      border-color: #6366f1;
      box-shadow: 0 0 0 3px rgba(99,102,241,0.1);
    }
    .optional {
      font-weight: 400;
      color: #999;
      font-size: 0.75rem;
    }
    button {
      width: 100%;
      padding: 0.75rem;
      background: #4f46e5;
      color: #fff;
      border: none;
      border-radius: 8px;
      font-size: 1rem;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.15s;
    }
    button:hover { background: #4338ca; }
    button:active { background: #3730a3; }
    .info {
      margin-top: 1rem;
      font-size: 0.75rem;
      color: #888;
      text-align: center;
      line-height: 1.4;
    }
  </style>
</head>
<body>
  <div class="card">
    <div class="logo">
      <h1>Monarch Money MCP</h1>
      <p>Sign in with your Monarch Money account</p>
    </div>
    ${errorHtml}
    <form method="POST" action="/oauth/authorize">
      <input type="hidden" name="client_id" value="${escapeAttr(params.clientId)}" />
      <input type="hidden" name="redirect_uri" value="${escapeAttr(params.redirectUri)}" />
      <input type="hidden" name="state" value="${escapeAttr(params.state)}" />
      <input type="hidden" name="code_challenge" value="${escapeAttr(params.codeChallenge)}" />
      <input type="hidden" name="code_challenge_method" value="${escapeAttr(params.codeChallengeMethod)}" />

      <label for="email">Email</label>
      <input type="email" id="email" name="email" required autocomplete="email" placeholder="you@example.com" />

      <label for="password">Password</label>
      <input type="password" id="password" name="password" required autocomplete="current-password" />

      <label for="mfa_secret">MFA Secret <span class="optional">(optional)</span></label>
      <input type="text" id="mfa_secret" name="mfa_secret" autocomplete="one-time-code" placeholder="Base32 TOTP secret" />

      <button type="submit">Authorize</button>
    </form>
    <p class="info">
      Your credentials are used only to authenticate with Monarch Money.<br/>
      They are never stored by this server.
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
