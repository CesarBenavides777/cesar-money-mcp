export interface Config {
  monarch: {
    email: string;
    password: string;
    mfaSecret?: string;
  };
  server: {
    port: number;
    transport: "stdio" | "http";
    corsOrigins: string[];
  };
  oauth: {
    clientId: string;
    clientSecret: string;
  };
  rateLimit: {
    rpm: number;
  };
  dbPath: string;
  logLevel: string;
}

export function loadConfig(): Config {
  const transport = resolveTransport();

  return {
    monarch: {
      email: requireEnv("MONARCH_EMAIL"),
      password: requireEnv("MONARCH_PASSWORD"),
      mfaSecret: process.env.MONARCH_MFA_SECRET || undefined,
    },
    server: {
      port: parseInt(process.env.PORT || "3200", 10),
      transport,
      corsOrigins: (
        process.env.CORS_ORIGINS ||
        "https://claude.ai,https://www.claude.ai,https://claude.com"
      ).split(","),
    },
    oauth: {
      clientId: process.env.OAUTH_CLIENT_ID || "",
      clientSecret: process.env.OAUTH_CLIENT_SECRET || "",
    },
    rateLimit: {
      rpm: parseInt(process.env.RATE_LIMIT_RPM || "60", 10),
    },
    dbPath: process.env.DB_PATH || "monarch-mcp.db",
    logLevel: process.env.LOG_LEVEL || "info",
  };
}

function resolveTransport(): "stdio" | "http" {
  // CLI flag takes precedence
  const args = process.argv.slice(2);
  const transportIdx = args.indexOf("--transport");
  if (transportIdx !== -1 && args[transportIdx + 1]) {
    const val = args[transportIdx + 1];
    if (val === "stdio" || val === "http") return val;
  }

  // Then env var
  const envTransport = process.env.TRANSPORT;
  if (envTransport === "stdio" || envTransport === "http") return envTransport;

  // Default
  return "stdio";
}

function requireEnv(key: string): string {
  const value = process.env[key];
  if (!value) {
    throw new Error(`Missing required environment variable: ${key}`);
  }
  return value;
}
