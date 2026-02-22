import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { getMonarchClient } from "../monarch/client.js";

export function registerRecurringTools(server: McpServer) {
  server.tool(
    "get_recurring_transactions",
    "Get all recurring transactions including subscriptions, bills, and regular payments. Returns details about each recurring stream such as merchant, amount, frequency, and next expected date. Use this to help the user understand their fixed obligations, find subscriptions they may want to cancel, or estimate upcoming bills.",
    {},
    async () => {
      try {
        const client = await getMonarchClient();
        const data = await client.recurring.getRecurringStreams();
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
