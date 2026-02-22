import { Database } from "bun:sqlite";
import crypto from "node:crypto";

// ── Types ───────────────────────────────────────────────────────────────────

interface AuthCode {
  code: string;
  client_id: string;
  redirect_uri: string;
  code_challenge: string | null;
  code_challenge_method: string | null;
  created_at: number;
  expires_at: number;
}

interface TokenPair {
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
}

interface ClientRecord {
  client_id: string;
  client_name: string | null;
  redirect_uris: string;
  created_at: number;
}

// ── Constants ───────────────────────────────────────────────────────────────

const ACCESS_TOKEN_TTL = 60 * 60;           // 1 hour in seconds
const REFRESH_TOKEN_TTL = 30 * 24 * 60 * 60; // 30 days in seconds
const AUTH_CODE_TTL = 10 * 60;               // 10 minutes in seconds

// ── Database singleton ──────────────────────────────────────────────────────

let db: Database | null = null;

export function initTokenStore(dbPath = "monarch-mcp.db") {
  db = new Database(dbPath);
  db.run("PRAGMA journal_mode=WAL");
  db.run("PRAGMA busy_timeout=5000");

  db.run(`
    CREATE TABLE IF NOT EXISTS auth_codes (
      code TEXT PRIMARY KEY,
      client_id TEXT NOT NULL,
      redirect_uri TEXT NOT NULL,
      code_challenge TEXT,
      code_challenge_method TEXT,
      created_at INTEGER NOT NULL,
      expires_at INTEGER NOT NULL
    )
  `);

  db.run(`
    CREATE TABLE IF NOT EXISTS tokens (
      token TEXT PRIMARY KEY,
      type TEXT NOT NULL CHECK(type IN ('access', 'refresh')),
      client_id TEXT NOT NULL,
      created_at INTEGER NOT NULL,
      expires_at INTEGER NOT NULL
    )
  `);

  db.run(`
    CREATE TABLE IF NOT EXISTS clients (
      client_id TEXT PRIMARY KEY,
      client_name TEXT,
      redirect_uris TEXT NOT NULL,
      created_at INTEGER NOT NULL
    )
  `);
}

function getDb(): Database {
  if (!db) {
    throw new Error("Token store not initialized. Call initTokenStore() first.");
  }
  return db;
}

// ── Auth codes ──────────────────────────────────────────────────────────────

export function generateAuthCode(
  clientId: string,
  redirectUri: string,
  codeChallenge?: string,
  codeChallengeMethod?: string
): string {
  const store = getDb();
  const code = crypto.randomBytes(32).toString("hex");
  const now = Math.floor(Date.now() / 1000);

  store
    .prepare(
      `INSERT INTO auth_codes (code, client_id, redirect_uri, code_challenge, code_challenge_method, created_at, expires_at)
       VALUES (?, ?, ?, ?, ?, ?, ?)`
    )
    .run(
      code,
      clientId,
      redirectUri,
      codeChallenge ?? null,
      codeChallengeMethod ?? null,
      now,
      now + AUTH_CODE_TTL
    );

  return code;
}

export function consumeAuthCode(code: string): AuthCode | null {
  const store = getDb();
  const now = Math.floor(Date.now() / 1000);

  const row = store
    .prepare(
      `SELECT code, client_id, redirect_uri, code_challenge, code_challenge_method, created_at, expires_at
       FROM auth_codes WHERE code = ?`
    )
    .get(code) as AuthCode | undefined;

  if (!row) return null;

  // Always delete the code (single-use)
  store.prepare("DELETE FROM auth_codes WHERE code = ?").run(code);

  // Check expiry after deletion so the code cannot be replayed
  if (row.expires_at < now) return null;

  return row;
}

// ── Tokens ──────────────────────────────────────────────────────────────────

export function generateTokenPair(clientId: string): TokenPair {
  const store = getDb();
  const now = Math.floor(Date.now() / 1000);

  const accessToken = crypto.randomUUID();
  const refreshToken = crypto.randomUUID();

  store
    .prepare(
      `INSERT INTO tokens (token, type, client_id, created_at, expires_at) VALUES (?, 'access', ?, ?, ?)`
    )
    .run(accessToken, clientId, now, now + ACCESS_TOKEN_TTL);

  store
    .prepare(
      `INSERT INTO tokens (token, type, client_id, created_at, expires_at) VALUES (?, 'refresh', ?, ?, ?)`
    )
    .run(refreshToken, clientId, now, now + REFRESH_TOKEN_TTL);

  return {
    accessToken,
    refreshToken,
    expiresIn: ACCESS_TOKEN_TTL,
  };
}

export function validateAccessToken(token: string): boolean {
  const store = getDb();
  const now = Math.floor(Date.now() / 1000);

  const row = store
    .prepare(
      `SELECT token FROM tokens WHERE token = ? AND type = 'access' AND expires_at > ?`
    )
    .get(token, now) as { token: string } | undefined;

  return !!row;
}

export function refreshAccessToken(
  refreshToken: string
): TokenPair | null {
  const store = getDb();
  const now = Math.floor(Date.now() / 1000);

  const row = store
    .prepare(
      `SELECT token, client_id FROM tokens WHERE token = ? AND type = 'refresh' AND expires_at > ?`
    )
    .get(refreshToken, now) as
    | { token: string; client_id: string }
    | undefined;

  if (!row) return null;

  // Rotate: delete the old refresh token to prevent reuse
  store.prepare("DELETE FROM tokens WHERE token = ?").run(refreshToken);

  // Also delete any existing access tokens for this client to keep things tidy
  store
    .prepare(
      "DELETE FROM tokens WHERE client_id = ? AND type = 'access'"
    )
    .run(row.client_id);

  return generateTokenPair(row.client_id);
}

// ── Clients ─────────────────────────────────────────────────────────────────

export function registerClient(
  clientName: string,
  redirectUris: string[]
): { clientId: string } {
  const store = getDb();
  const clientId = crypto.randomUUID();
  const now = Math.floor(Date.now() / 1000);

  store
    .prepare(
      `INSERT INTO clients (client_id, client_name, redirect_uris, created_at) VALUES (?, ?, ?, ?)`
    )
    .run(clientId, clientName, JSON.stringify(redirectUris), now);

  return { clientId };
}

export function validateClient(clientId: string): boolean {
  const store = getDb();

  const row = store
    .prepare("SELECT client_id FROM clients WHERE client_id = ?")
    .get(clientId) as { client_id: string } | undefined;

  return !!row;
}

export function getClientRedirectUris(clientId: string): string[] {
  const store = getDb();

  const row = store
    .prepare("SELECT redirect_uris FROM clients WHERE client_id = ?")
    .get(clientId) as { redirect_uris: string } | undefined;

  if (!row) return [];

  try {
    return JSON.parse(row.redirect_uris) as string[];
  } catch {
    return [];
  }
}

// ── Maintenance ─────────────────────────────────────────────────────────────

export function cleanupExpired(): void {
  const store = getDb();
  const now = Math.floor(Date.now() / 1000);

  store.prepare("DELETE FROM auth_codes WHERE expires_at < ?").run(now);
  store.prepare("DELETE FROM tokens WHERE expires_at < ?").run(now);
}
