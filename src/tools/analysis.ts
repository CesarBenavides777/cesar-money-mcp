import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { getMonarchClient } from "../monarch/client.js";
import { analyzeSpending } from "../analysis/spending.js";
import { detectAnomalies } from "../analysis/anomalies.js";
import { forecastCashflow } from "../analysis/forecasting.js";
import { analyzeSubscriptions } from "../analysis/subscriptions.js";
import { detectTrends } from "../analysis/trends.js";
import { calculateHealthScore } from "../analysis/health.js";

export function registerAnalysisTools(server: McpServer) {
  server.tool(
    "analyze_spending",
    "Analyze spending patterns for a given time period with optional category filtering. Breaks down spending by category, identifies top merchants, calculates daily averages, and compares to previous periods. Use this when the user wants to understand where their money is going, find their biggest expenses, or compare spending across time periods. Returns category breakdowns, merchant rankings, and period-over-period changes.",
    {
      start_date: z
        .string()
        .optional()
        .describe(
          "Start date for the analysis period in YYYY-MM-DD format. Defaults to 30 days ago."
        ),
      end_date: z
        .string()
        .optional()
        .describe(
          "End date for the analysis period in YYYY-MM-DD format. Defaults to today."
        ),
      category: z
        .string()
        .optional()
        .describe(
          "Optional category name to filter the analysis. When provided, only transactions in this category are analyzed. Leave empty for a full cross-category breakdown."
        ),
    },
    async ({ start_date, end_date, category }) => {
      try {
        const client = await getMonarchClient();

        const now = new Date();
        const defaultStart = new Date(now);
        defaultStart.setDate(defaultStart.getDate() - 30);

        const startDate =
          start_date ?? defaultStart.toISOString().split("T")[0];
        const endDate = end_date ?? now.toISOString().split("T")[0];

        const paginatedTransactions = await client.transactions.getTransactions({
          startDate,
          endDate,
          limit: 5000,
        });

        let txList = paginatedTransactions.transactions as any[];
        if (category) {
          txList = txList.filter((tx: any) =>
            tx.category?.name?.toLowerCase() === category.toLowerCase()
          );
        }

        const result = analyzeSpending(txList, {
          startDate,
          endDate,
        });

        return {
          content: [
            { type: "text" as const, text: JSON.stringify(result, null, 2) },
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
    "detect_anomalies",
    "Scan recent transactions for anomalies including unusually large purchases, potential duplicate charges, transactions from new or unfamiliar merchants, and spending that deviates significantly from normal patterns. Use this when the user wants to audit their transactions, check for fraud, find billing errors, or identify unexpected charges. Returns categorized anomalies with severity levels and explanations.",
    {
      lookback_days: z
        .number()
        .optional()
        .describe(
          "Number of days to look back for anomaly detection. Defaults to 90. Larger windows provide better baseline data for detecting outliers but take longer to process."
        ),
    },
    async ({ lookback_days }) => {
      try {
        const client = await getMonarchClient();

        const days = lookback_days ?? 90;
        const now = new Date();
        const startDate = new Date(now);
        startDate.setDate(startDate.getDate() - days);

        const paginatedTransactions = await client.transactions.getTransactions({
          startDate: startDate.toISOString().split("T")[0],
          endDate: now.toISOString().split("T")[0],
          limit: 5000,
        });

        const result = detectAnomalies(paginatedTransactions.transactions as any);

        return {
          content: [
            { type: "text" as const, text: JSON.stringify(result, null, 2) },
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
    "forecast_cashflow",
    "Project future cash flow based on historical income, expenses, and recurring transactions. Uses account balances, recent transaction patterns, and scheduled recurring items to forecast balances for 30, 60, and 90 day horizons. Use this when the user wants to know if they can afford an upcoming expense, plan for future savings, or understand their financial trajectory. Returns projected balances, expected income and expenses, and confidence intervals.",
    {
      days_ahead: z
        .number()
        .optional()
        .describe(
          "Number of days to forecast into the future. Defaults to 30. Supported values are typically 30, 60, or 90 days."
        ),
    },
    async ({ days_ahead }) => {
      try {
        const client = await getMonarchClient();

        const days = days_ahead ?? 30;
        const now = new Date();
        const lookbackStart = new Date(now);
        lookbackStart.setDate(lookbackStart.getDate() - 90);

        const [accounts, paginatedTransactions, recurringStreams] = await Promise.all([
          client.accounts.getAll(),
          client.transactions.getTransactions({
            startDate: lookbackStart.toISOString().split("T")[0],
            endDate: now.toISOString().split("T")[0],
            limit: 5000,
          }),
          client.recurring.getRecurringStreams(),
        ]);

        // Map recurring streams to the RecurringItem shape expected by forecastCashflow
        const today = new Date().toISOString().split("T")[0];
        const recurringItems = recurringStreams.map((r) => ({
          id: r.stream.id,
          merchant: r.stream.merchant.name,
          amount: r.stream.amount,
          frequency: r.stream.frequency as any,
          nextDate: (r.stream.baseDate ?? today) as string,
        }));

        const result = forecastCashflow(
          accounts as any,
          paginatedTransactions.transactions as any,
          recurringItems as any,
          { forecastDays: days }
        );

        return {
          content: [
            { type: "text" as const, text: JSON.stringify(result, null, 2) },
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
    "track_subscriptions",
    "Analyze all recurring payments and subscriptions to identify active services, detect recent price changes, calculate total monthly and annual subscription costs, and find potentially forgotten or unused subscriptions. Use this when the user wants to review what they're paying for on a recurring basis, find ways to save money, or track subscription creep over time. Returns a detailed list of subscriptions with cost breakdowns and change history.",
    {},
    async () => {
      try {
        const client = await getMonarchClient();

        const recurringStreams = await client.recurring.getRecurringStreams();

        // Map to the RecurringTransaction shape expected by analyzeSubscriptions
        const todayStr = new Date().toISOString().split("T")[0];
        const recurring = recurringStreams.map((r) => ({
          id: r.stream.id,
          date: (r.stream.baseDate ?? todayStr) as string,
          amount: r.stream.amount,
          merchant: r.stream.merchant.name,
        }));

        const result = analyzeSubscriptions(recurring);

        return {
          content: [
            { type: "text" as const, text: JSON.stringify(result, null, 2) },
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
    "detect_trends",
    "Identify spending trends over multiple months by analyzing how spending in each category changes over time. Detects categories with increasing or decreasing spending, seasonal patterns, and significant shifts. Use this when the user wants to understand long-term spending direction, identify lifestyle inflation, or spot gradual changes they might not notice month-to-month. Returns trend data with direction, magnitude, and statistical significance for each category.",
    {
      months: z
        .number()
        .optional()
        .describe(
          "Number of months of historical data to analyze for trend detection. Defaults to 6. Longer periods provide more reliable trend identification."
        ),
      category: z
        .string()
        .optional()
        .describe(
          "Optional category name to focus trend analysis on. When provided, returns detailed trend data for just this category. Leave empty to analyze trends across all categories."
        ),
    },
    async ({ months, category }) => {
      try {
        const client = await getMonarchClient();

        const numMonths = months ?? 6;
        const now = new Date();
        const startDate = new Date(now);
        startDate.setMonth(startDate.getMonth() - numMonths);

        const paginatedTransactions = await client.transactions.getTransactions({
          startDate: startDate.toISOString().split("T")[0],
          endDate: now.toISOString().split("T")[0],
          limit: 10000,
        });

        const result = detectTrends(paginatedTransactions.transactions as any, {
          minMonths: Math.min(numMonths, 3),
          categories: category ? [category] : undefined,
        });

        return {
          content: [
            { type: "text" as const, text: JSON.stringify(result, null, 2) },
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
    "get_financial_health_score",
    "Calculate a comprehensive financial health score from 0 to 100 based on multiple factors including savings rate, debt-to-income ratio, emergency fund adequacy, budget adherence, net worth trajectory, and account diversification. Use this when the user wants an overall assessment of their financial wellness, wants to track improvement over time, or needs a high-level summary of their financial situation. Returns the overall score, individual component scores, and actionable recommendations for improvement.",
    {},
    async () => {
      try {
        const client = await getMonarchClient();

        const now = new Date();
        const lookbackStart = new Date(now);
        lookbackStart.setDate(lookbackStart.getDate() - 90);

        const currentMonthStart = new Date(
          now.getFullYear(),
          now.getMonth(),
          1
        );
        const currentMonthEnd = new Date(
          now.getFullYear(),
          now.getMonth() + 1,
          0
        );

        const [rawAccounts, paginatedTransactions, budgetData, netWorthHistory] =
          await Promise.all([
            client.accounts.getAll(),
            client.transactions.getTransactions({
              startDate: lookbackStart.toISOString().split("T")[0],
              endDate: now.toISOString().split("T")[0],
              limit: 5000,
            }),
            client.budgets.getBudgets({
              startDate: currentMonthStart.toISOString().split("T")[0],
              endDate: currentMonthEnd.toISOString().split("T")[0],
            }),
            client.accounts.getNetWorthHistory(),
          ]);

        // Map Account[] to HealthAccount[] by converting type object to string
        const typeMap: Record<string, "depository" | "investment" | "credit" | "loan" | "mortgage" | "other"> = {
          depository: "depository",
          investment: "investment",
          credit: "credit",
          loan: "loan",
          mortgage: "mortgage",
        };
        const accounts = rawAccounts.map((a) => ({
          id: a.id,
          displayName: a.displayName,
          currentBalance: a.currentBalance,
          type: typeMap[a.type.name] ?? "other" as const,
        }));

        // Extract BudgetItem[] from BudgetData
        const budgets = budgetData.budgetData.monthlyAmountsByCategory.map((item) => ({
          category: item.category.id,
          budgeted: item.monthlyAmounts[0]?.plannedCashFlowAmount ?? 0,
          actual: Math.abs(item.monthlyAmounts[0]?.actualAmount ?? 0),
        }));

        const result = calculateHealthScore({
          accounts,
          transactions: paginatedTransactions.transactions as any,
          budgets,
          netWorthHistory,
        });

        return {
          content: [
            { type: "text" as const, text: JSON.stringify(result, null, 2) },
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
