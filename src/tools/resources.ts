import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { getMonarchClient } from "../monarch/client.js";

export function registerResources(server: McpServer) {
  server.registerResource(
    "accounts",
    "finance://accounts",
    { description: "All linked financial accounts with current balances" },
    async (uri) => {
      const client = await getMonarchClient();
      const accounts = await client.accounts.getAll();
      return {
        contents: [
          {
            uri: uri.href,
            mimeType: "application/json",
            text: JSON.stringify(accounts, null, 2),
          },
        ],
      };
    }
  );

  server.registerResource(
    "net-worth",
    "finance://net-worth",
    { description: "Net worth snapshot with asset/liability breakdown and history" },
    async (uri) => {
      const client = await getMonarchClient();
      const accounts = await client.accounts.getAll();
      const netWorthHistory = await client.accounts.getNetWorthHistory();

      const liabilityTypes = new Set(["credit", "loan", "liability", "mortgage"]);

      const totalAssets = accounts
        .filter((a: any) => !liabilityTypes.has(a.type?.name ?? a.type))
        .reduce((sum: number, a: any) => sum + (a.currentBalance ?? 0), 0);

      const totalLiabilities = accounts
        .filter((a: any) => liabilityTypes.has(a.type?.name ?? a.type))
        .reduce(
          (sum: number, a: any) => sum + Math.abs(a.currentBalance ?? 0),
          0
        );

      const snapshot = {
        totalAssets,
        totalLiabilities,
        netWorth: totalAssets - totalLiabilities,
        accountBreakdown: accounts.map((a: any) => ({
          name: a.displayName ?? a.name,
          type: a.type,
          balance: a.currentBalance,
          institution: a.institution?.name,
        })),
        history: netWorthHistory,
      };

      return {
        contents: [
          {
            uri: uri.href,
            mimeType: "application/json",
            text: JSON.stringify(snapshot, null, 2),
          },
        ],
      };
    }
  );

  server.registerResource(
    "budget-current",
    "finance://budget/current",
    { description: "Current month budget with planned vs actual amounts" },
    async (uri) => {
      const client = await getMonarchClient();

      const now = new Date();
      const startDate = new Date(now.getFullYear(), now.getMonth(), 1);
      const endDate = new Date(now.getFullYear(), now.getMonth() + 1, 0);

      const budgets = await client.budgets.getBudgets({
        startDate: startDate.toISOString().split("T")[0],
        endDate: endDate.toISOString().split("T")[0],
      });

      return {
        contents: [
          {
            uri: uri.href,
            mimeType: "application/json",
            text: JSON.stringify(budgets, null, 2),
          },
        ],
      };
    }
  );

  server.registerResource(
    "subscriptions",
    "finance://subscriptions",
    { description: "All recurring payments and subscription data" },
    async (uri) => {
      const client = await getMonarchClient();
      const recurring = await client.recurring.getRecurringStreams();

      return {
        contents: [
          {
            uri: uri.href,
            mimeType: "application/json",
            text: JSON.stringify(recurring, null, 2),
          },
        ],
      };
    }
  );
}
