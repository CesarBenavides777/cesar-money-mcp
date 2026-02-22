import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { getMonarchClient } from "../monarch/client.js";

export function registerInsightTools(server: McpServer) {
  server.registerTool(
    "get_net_worth",
    {
      description:
        "Get the current net worth snapshot by fetching the most recent net worth data point. Returns total assets, total liabilities, and net worth as of today. Use this when the user asks 'what is my net worth?' or wants a quick financial health summary.",
      annotations: { readOnlyHint: true },
    },
    async () => {
      try {
        const client = await getMonarchClient();
        const today = new Date().toISOString().split("T")[0];
        const data = await client.insights.getNetWorthHistory({
          startDate: today,
          endDate: today,
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
    "get_net_worth_history",
    {
      description:
        "Get net worth history over a date range showing how total assets, liabilities, and net worth have changed over time. Returns a time series of data points useful for charting net worth growth, identifying trends, or measuring progress toward financial goals.",
      inputSchema: {
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
      annotations: { readOnlyHint: true },
    },
    async ({ startDate, endDate }) => {
      try {
        const client = await getMonarchClient();
        const data = await client.insights.getNetWorthHistory({
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
