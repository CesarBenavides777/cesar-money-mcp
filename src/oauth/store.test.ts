import { describe, expect, test, beforeEach, afterEach } from "bun:test";
import { unlinkSync, existsSync } from "node:fs";
import {
  initTokenStore,
  generateAuthCode,
  consumeAuthCode,
  generateTokenPair,
  validateAccessToken,
  refreshAccessToken,
  registerClient,
  validateClient,
  getClientRedirectUris,
  cleanupExpired,
} from "./store.js";

const TEST_DB = "/tmp/monarch-mcp-test.db";

beforeEach(() => {
  // Clean up any existing test DB
  for (const suffix of ["", "-shm", "-wal"]) {
    const path = TEST_DB + suffix;
    if (existsSync(path)) unlinkSync(path);
  }
  initTokenStore(TEST_DB);
});

afterEach(() => {
  for (const suffix of ["", "-shm", "-wal"]) {
    const path = TEST_DB + suffix;
    if (existsSync(path)) unlinkSync(path);
  }
});

describe("Client Registration", () => {
  test("registers a client and validates it", () => {
    const { clientId } = registerClient("Test App", ["http://localhost:3000/callback"]);
    expect(clientId).toBeDefined();
    expect(typeof clientId).toBe("string");
    expect(validateClient(clientId)).toBe(true);
  });

  test("returns false for unknown client", () => {
    expect(validateClient("nonexistent-id")).toBe(false);
  });

  test("stores and retrieves redirect URIs", () => {
    const uris = ["http://localhost:3000/callback", "http://localhost:4000/auth"];
    const { clientId } = registerClient("Test App", uris);
    const retrieved = getClientRedirectUris(clientId);
    expect(retrieved).toEqual(uris);
  });

  test("returns empty array for unknown client redirect URIs", () => {
    expect(getClientRedirectUris("nonexistent")).toEqual([]);
  });
});

describe("Auth Codes", () => {
  test("generates and consumes an auth code", () => {
    const { clientId } = registerClient("Test", ["http://localhost/cb"]);
    const code = generateAuthCode(clientId, "http://localhost/cb", "challenge", "S256");

    expect(typeof code).toBe("string");
    expect(code.length).toBe(64); // 32 bytes hex

    const consumed = consumeAuthCode(code);
    expect(consumed).not.toBeNull();
    expect(consumed!.client_id).toBe(clientId);
    expect(consumed!.code_challenge).toBe("challenge");
    expect(consumed!.code_challenge_method).toBe("S256");
  });

  test("auth code is single-use (cannot be consumed twice)", () => {
    const { clientId } = registerClient("Test", ["http://localhost/cb"]);
    const code = generateAuthCode(clientId, "http://localhost/cb");

    const first = consumeAuthCode(code);
    expect(first).not.toBeNull();

    const second = consumeAuthCode(code);
    expect(second).toBeNull();
  });

  test("returns null for non-existent code", () => {
    expect(consumeAuthCode("nonexistent")).toBeNull();
  });
});

describe("Tokens", () => {
  test("generates a valid access token", () => {
    const { clientId } = registerClient("Test", ["http://localhost/cb"]);
    const { accessToken, refreshToken, expiresIn } = generateTokenPair(clientId);

    expect(typeof accessToken).toBe("string");
    expect(typeof refreshToken).toBe("string");
    expect(expiresIn).toBe(3600); // 1 hour
    expect(validateAccessToken(accessToken)).toBe(true);
  });

  test("rejects invalid access token", () => {
    expect(validateAccessToken("invalid-token")).toBe(false);
  });

  test("refresh token generates new token pair", () => {
    const { clientId } = registerClient("Test", ["http://localhost/cb"]);
    const original = generateTokenPair(clientId);

    const refreshed = refreshAccessToken(original.refreshToken);
    expect(refreshed).not.toBeNull();
    expect(refreshed!.accessToken).not.toBe(original.accessToken);
    expect(refreshed!.refreshToken).not.toBe(original.refreshToken);

    // New access token should be valid
    expect(validateAccessToken(refreshed!.accessToken)).toBe(true);
    // Old access token should be invalid (cleaned up during refresh)
    expect(validateAccessToken(original.accessToken)).toBe(false);
  });

  test("refresh token is single-use", () => {
    const { clientId } = registerClient("Test", ["http://localhost/cb"]);
    const { refreshToken } = generateTokenPair(clientId);

    const first = refreshAccessToken(refreshToken);
    expect(first).not.toBeNull();

    const second = refreshAccessToken(refreshToken);
    expect(second).toBeNull();
  });

  test("returns null for invalid refresh token", () => {
    expect(refreshAccessToken("invalid")).toBeNull();
  });
});

describe("Cleanup", () => {
  test("cleanupExpired runs without error", () => {
    const { clientId } = registerClient("Test", ["http://localhost/cb"]);
    generateAuthCode(clientId, "http://localhost/cb");
    generateTokenPair(clientId);

    // Should not throw
    expect(() => cleanupExpired()).not.toThrow();
  });
});
