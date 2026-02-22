import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { getMonarchClient } from "../monarch/client.js";

export function registerResources(server: McpServer) {
  server.resource(
    "accounts",
    "finance://accounts",
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

  server.resource(
    "net-worth",
    "finance://net-worth",
    async (uri) => {
      const client = await getMonarchClient();
      const accounts = await client.accounts.getAll();
      const netWorthHistory = await client.accounts.getNetWorthHistory();

      const totalAssets = accounts
        .filter(
          (a: any) =>
            a.type !== "credit" && a.type !== "loan" && a.type !== "liability"
        )
        .reduce((sum: number, a: any) => sum + (a.currentBalance ?? 0), 0);

      const totalLiabilities = accounts
        .filter(
          (a: any) =>
            a.type === "credit" || a.type === "loan" || a.type === "liability"
        )
        .reduce((sum: number, a: any) => sum + (a.currentBalance ?? 0), 0);

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

  server.resource(
    "budget-current",
    "finance://budget/current",
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

  server.resource(
    "subscriptions",
    "finance://subscriptions",
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
