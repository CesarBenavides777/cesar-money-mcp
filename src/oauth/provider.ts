import { MonarchClient } from "monarchmoney";

/**
 * Validate user-supplied Monarch Money credentials by attempting a login.
 *
 * This does NOT store credentials — it simply verifies that the email/password
 * (and optional MFA secret) are correct so we can issue an OAuth token.
 */
export async function validateMonarchCredentials(
  email: string,
  password: string,
  mfaSecret?: string
): Promise<{ valid: boolean; error?: string }> {
  try {
    const client = new MonarchClient({
      timeout: 30_000,
      retries: 1,
      retryDelay: 1000,
    });

    await client.login({
      email,
      password,
      mfaSecretKey: mfaSecret || undefined,
      saveSession: false,
    });

    return { valid: true };
  } catch (err: unknown) {
    const message =
      err instanceof Error ? err.message : "Unknown authentication error";

    // Provide user-friendly error messages for common failures
    if (message.toLowerCase().includes("mfa") || message.toLowerCase().includes("multi-factor")) {
      return {
        valid: false,
        error: "Multi-factor authentication is required. Please provide your MFA secret.",
      };
    }

    if (message.toLowerCase().includes("unauthorized") || message.toLowerCase().includes("invalid")) {
      return {
        valid: false,
        error: "Invalid email or password.",
      };
    }

    return {
      valid: false,
      error: `Authentication failed: ${message}`,
    };
  }
}
