import { MonarchClient } from "monarchmoney";

let clientInstance: MonarchClient | null = null;
let loginPromise: Promise<MonarchClient> | null = null;

/**
 * Get an authenticated MonarchMoney client (singleton).
 * Reuses the same session across tool calls for efficiency.
 */
export async function getMonarchClient(): Promise<MonarchClient> {
  if (clientInstance) {
    // Validate existing session is still good
    try {
      const valid = await clientInstance.validateSession();
      if (valid) return clientInstance;
    } catch {
      // Session expired — re-login
      clientInstance = null;
    }
  }

  // Prevent concurrent login attempts
  if (loginPromise) return loginPromise;

  loginPromise = createClient();
  try {
    clientInstance = await loginPromise;
    return clientInstance;
  } finally {
    loginPromise = null;
  }
}

async function createClient(): Promise<MonarchClient> {
  const email = process.env.MONARCH_EMAIL;
  const password = process.env.MONARCH_PASSWORD;
  const mfaSecret = process.env.MONARCH_MFA_SECRET;

  if (!email || !password) {
    throw new Error(
      "MONARCH_EMAIL and MONARCH_PASSWORD environment variables are required"
    );
  }

  const client = new MonarchClient({
    timeout: 30_000,
    retries: 3,
    retryDelay: 1000,
    cache: {
      memoryTTL: {
        accounts: 300_000,
        categories: 300_000,
        transactions: 300_000,
        budgets: 300_000,
      },
      persistentTTL: {
        session: 86_400_000,
        userProfile: 3_600_000,
      },
      autoInvalidate: true,
      maxMemorySize: 500,
    },
  });

  await client.login({
    email,
    password,
    mfaSecretKey: mfaSecret,
    saveSession: true,
  });

  return client;
}

/**
 * Clear the cached client (e.g., on auth error).
 */
export function resetMonarchClient(): void {
  clientInstance = null;
  loginPromise = null;
}
