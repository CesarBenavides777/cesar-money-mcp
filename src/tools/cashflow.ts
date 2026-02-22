import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { getMonarchClient } from "../monarch/client.js";

export function registerCashflowTools(server: McpServer) {
  server.registerTool(
    "get_cashflow",
    {
      description:
        "Get detailed cash flow data showing income and expense breakdowns over a time period. Returns granular category-level spending and income data useful for understanding where money is coming from and going to. Use this for detailed cash flow analysis or when the user wants to drill into specific income/expense categories.",
      inputSchema: {
        startDate: z
          .string()
          .optional()
          .describe(
            "Start date for the cash flow period in YYYY-MM-DD format. Defaults to the current month start."
          ),
        endDate: z
          .string()
          .optional()
          .describe(
            "End date for the cash flow period in YYYY-MM-DD format. Defaults to the current month end."
          ),
      },
      annotations: { readOnlyHint: true },
    },
    async ({ startDate, endDate }) => {
      try {
        const client = await getMonarchClient();
        const data = await client.budgets.getCashFlow({
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

  server.registerTool(
    "get_cashflow_summary",
    {
      description:
        "Get a high-level cash flow summary showing total income versus total expenses for a time period. Returns aggregated totals and the net savings/deficit. Use this for a quick overview of whether the user is saving or overspending, or for simple income-vs-expense comparisons.",
      inputSchema: {
        startDate: z
          .string()
          .optional()
          .describe(
            "Start date for the summary period in YYYY-MM-DD format. Defaults to the current month start."
          ),
        endDate: z
          .string()
          .optional()
          .describe(
            "End date for the summary period in YYYY-MM-DD format. Defaults to the current month end."
          ),
      },
      annotations: { readOnlyHint: true },
    },
    async ({ startDate, endDate }) => {
      try {
        const client = await getMonarchClient();
        const data = await client.budgets.getCashFlowSummary({
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
