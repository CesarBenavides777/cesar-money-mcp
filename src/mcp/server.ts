import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { registerAccountTools } from "../tools/accounts.js";
import { registerTransactionTools } from "../tools/transactions.js";
import { registerBudgetTools } from "../tools/budgets.js";
import { registerCashflowTools } from "../tools/cashflow.js";
import { registerRecurringTools } from "../tools/recurring.js";
import { registerCategoryTools } from "../tools/categories.js";
import { registerInstitutionTools } from "../tools/institutions.js";
import { registerInsightTools } from "../tools/insights.js";
import { registerAnalysisTools } from "../tools/analysis.js";
import { registerResources } from "../tools/resources.js";
import { registerPrompts } from "../tools/prompts.js";

const SERVER_NAME = "monarch-money";
const SERVER_VERSION = "1.0.0";

/**
 * Create and configure a fully-loaded MCP server instance
 * with all tools, resources, and prompts registered.
 */
export function createMcpServer(): McpServer {
  const server = new McpServer({
    name: SERVER_NAME,
    version: SERVER_VERSION,
  });

  // Data tools — direct Monarch Money API access
  registerAccountTools(server);
  registerTransactionTools(server);
  registerBudgetTools(server);
  registerCashflowTools(server);
  registerRecurringTools(server);
  registerCategoryTools(server);
  registerInstitutionTools(server);
  registerInsightTools(server);

  // Analysis tools — computed insights
  registerAnalysisTools(server);

  // Resources — read-only data surfaces
  registerResources(server);

  // Prompts — canned analysis templates
  registerPrompts(server);

  return server;
}
