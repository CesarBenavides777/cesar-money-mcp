import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { getMonarchClient } from "../monarch/client.js";

export function registerTransactionTools(server: McpServer) {
  server.tool(
    "get_transactions",
    "Retrieve a paginated list of transactions with optional filters. Use this to browse recent spending, filter transactions by date range, category, or account, or to get raw transaction data for analysis. Supports pagination for large result sets. Returns transaction amounts, dates, merchants, categories, and account info.",
    {
      limit: z
        .number()
        .optional()
        .describe(
          "Maximum number of transactions to return. Defaults to 50. Use smaller values for quick lookups, larger for comprehensive analysis."
        ),
      offset: z
        .number()
        .optional()
        .describe(
          "Number of transactions to skip for pagination. Use with limit to page through results."
        ),
      startDate: z
        .string()
        .optional()
        .describe(
          "Filter transactions on or after this date in YYYY-MM-DD format."
        ),
      endDate: z
        .string()
        .optional()
        .describe(
          "Filter transactions on or before this date in YYYY-MM-DD format."
        ),
      categoryId: z
        .string()
        .optional()
        .describe(
          "Filter by category ID. Obtain category IDs from get_categories."
        ),
      accountId: z
        .string()
        .optional()
        .describe(
          "Filter by account ID. Obtain account IDs from get_accounts."
        ),
    },
    async ({ limit, offset, startDate, endDate, categoryId, accountId }) => {
      try {
        const client = await getMonarchClient();
        const data = await client.transactions.getTransactions({
          limit: limit ?? 50,
          offset: offset ?? 0,
          startDate,
          endDate,
          categoryIds: categoryId ? [categoryId] : undefined,
          accountIds: accountId ? [accountId] : undefined,
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
    "search_transactions",
    "Search transactions by merchant name or description text. Use this when the user asks about spending at a specific store, vendor, or service, or wants to find transactions matching a keyword. More targeted than get_transactions for text-based lookups.",
    {
      search: z
        .string()
        .describe(
          "Search query to match against merchant names and transaction descriptions."
        ),
      limit: z
        .number()
        .optional()
        .describe(
          "Maximum number of results to return. Defaults to 50."
        ),
      startDate: z
        .string()
        .optional()
        .describe(
          "Filter results on or after this date in YYYY-MM-DD format."
        ),
      endDate: z
        .string()
        .optional()
        .describe(
          "Filter results on or before this date in YYYY-MM-DD format."
        ),
    },
    async ({ search, limit, startDate, endDate }) => {
      try {
        const client = await getMonarchClient();
        const data = await client.transactions.getTransactions({
          search,
          limit: limit ?? 50,
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
