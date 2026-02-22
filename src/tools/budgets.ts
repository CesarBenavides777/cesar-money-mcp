import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { getMonarchClient } from "../monarch/client.js";

export function registerBudgetTools(server: McpServer) {
  server.registerTool(
    "get_budgets",
    {
      description:
        "Retrieve budget data for a given time period, including budget categories, planned amounts, actual spending, and remaining balances. Use this to check how spending compares to budgeted amounts, identify categories that are over or under budget, or get a complete picture of the user's budgeting setup.",
      inputSchema: {
        startDate: z
          .string()
          .optional()
          .describe(
            "Start date for the budget period in YYYY-MM-DD format. Typically the first day of a month. Defaults to the current month start."
          ),
        endDate: z
          .string()
          .optional()
          .describe(
            "End date for the budget period in YYYY-MM-DD format. Typically the last day of a month. Defaults to the current month end."
          ),
      },
      annotations: { readOnlyHint: true },
    },
    async ({ startDate, endDate }) => {
      try {
        const client = await getMonarchClient();
        const data = await client.budgets.getBudgets({
          startDate,
          endDate,
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
}
