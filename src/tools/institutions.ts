import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { getMonarchClient } from "../monarch/client.js";

export function registerInstitutionTools(server: McpServer) {
  server.registerTool(
    "get_institutions",
    {
      description:
        "Get all financial institutions (banks, brokerages, credit unions, etc.) linked to the Monarch Money account. Returns institution names, connection status, last sync times, and associated accounts. Use this to check which institutions are connected, diagnose sync issues, or get an overview of all linked financial providers.",
      annotations: { readOnlyHint: true },
    },
    async () => {
      try {
        const client = await getMonarchClient();
        const data = await client.institutions.getInstitutions();
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
