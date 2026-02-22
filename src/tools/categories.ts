import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { getMonarchClient } from "../monarch/client.js";

export function registerCategoryTools(server: McpServer) {
  server.registerTool(
    "get_categories",
    {
      description:
        "Get all transaction categories configured in Monarch Money. Returns category names, IDs, and types (income vs expense). Use this to look up category IDs for filtering transactions or budgets, or to understand the user's category taxonomy.",
      annotations: { readOnlyHint: true },
    },
    async () => {
      try {
        const client = await getMonarchClient();
        const data = await client.categories.getCategories();
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
    "get_category_groups",
    {
      description:
        "Get all category groups which organize individual categories into higher-level groupings (e.g., 'Food & Drink' containing 'Groceries' and 'Restaurants'). Use this to understand the hierarchical structure of categories or to aggregate spending at a group level.",
      annotations: { readOnlyHint: true },
    },
    async () => {
      try {
        const client = await getMonarchClient();
        const data = await client.categories.getCategoryGroups();
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
