import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { getMonarchClient } from "../monarch/client.js";

export function registerAccountTools(server: McpServer) {
  server.tool(
    "get_accounts",
    "List all financial accounts linked to Monarch Money, including bank accounts, credit cards, investments, loans, and other assets. Returns account names, types, current balances, and institution details. Use this to get an overview of all connected accounts or find a specific account ID for further queries.",
    {
      includeHidden: z
        .boolean()
        .optional()
        .describe(
          "Whether to include hidden/archived accounts in the results. Defaults to false."
        ),
    },
    async ({ includeHidden }) => {
      try {
        const client = await getMonarchClient();
        const data = await client.accounts.getAll({
          includeHidden: includeHidden ?? false,
        });
        return {
          content: [
            { type: "text" as const, text: JSON.stringify(data, null, 2) },
          ],
        };
      } catch (error) {
        const message =
          error instanceof Error ? error.message : String(error);
        return {
          content: [{ type: "text" as const, text: `Error: ${message}` }],
          isError: true,
        };
      }
    }
  );

  server.tool(
    "get_account_history",
    "Get the balance history for a specific account over time. Returns a time series of balance snapshots useful for charting account growth, tracking debt payoff progress, or analyzing balance trends. Requires an account ID which can be obtained from get_accounts.",
    {
      accountId: z
        .string()
        .describe(
          "The unique identifier of the account to get history for. Obtain this from get_accounts."
        ),
      startDate: z
        .string()
        .optional()
        .describe(
          "Start date for the history range in YYYY-MM-DD format. Defaults to the earliest available data."
        ),
      endDate: z
        .string()
        .optional()
        .describe(
          "End date for the history range in YYYY-MM-DD format. Defaults to today."
        ),
    },
    async ({ accountId, startDate, endDate }) => {
      try {
        const client = await getMonarchClient();
        const data = await client.accounts.getHistory(
          accountId,
          startDate,
          endDate
        );
        return {
          content: [
            { type: "text" as const, text: JSON.stringify(data, null, 2) },
          ],
        };
      } catch (error) {
        const message =
          error instanceof Error ? error.message : String(error);
        return {
          content: [{ type: "text" as const, text: `Error: ${message}` }],
          isError: true,
        };
      }
    }
  );
}
