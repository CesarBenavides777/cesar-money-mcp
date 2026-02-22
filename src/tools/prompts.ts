import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

export function registerPrompts(server: McpServer) {
  server.registerPrompt(
    "monthly-review",
    {
      description:
        "Comprehensive monthly financial review covering accounts, cash flow, spending, anomalies, and overall financial health",
    },
    async () => ({
      messages: [
        {
          role: "user" as const,
          content: {
            type: "text" as const,
            text: "Please provide a comprehensive monthly financial review. Use these tools in order:\n\n1. **get_accounts** - Show current account balances and highlight any significant changes\n2. **get_cashflow_summary** - Show income vs expenses for this month and calculate the savings rate\n3. **analyze_spending** - Break down spending by category, identify the top 5 expense categories\n4. **detect_anomalies** - Flag any unusual transactions, potential duplicates, or new merchants\n5. **get_financial_health_score** - Calculate the overall financial health score\n\nFormat the review as a clear, actionable report with the following sections:\n- **Account Summary**: Current balances across all accounts\n- **Cash Flow Overview**: Income vs expenses, net savings or deficit\n- **Spending Breakdown**: Category-by-category analysis with percentages\n- **Alerts & Anomalies**: Any transactions that need attention\n- **Health Score**: Overall score with component breakdown\n- **Recommendations**: 3-5 specific, actionable steps to improve finances this month",
          },
        },
      ],
    })
  );

  server.registerPrompt(
    "budget-check",
    {
      description:
        "Check current month budget adherence, identify over-budget categories, and project end-of-month outcomes",
    },
    async () => ({
      messages: [
        {
          role: "user" as const,
          content: {
            type: "text" as const,
            text: "Please check my budget adherence for the current month. Use these tools:\n\n1. **get_budgets** - Get the current month's budget with planned vs actual amounts\n2. **get_cashflow** - Get detailed cash flow to see category-level spending\n3. **analyze_spending** - Analyze spending patterns for the current month\n\nProvide a report with:\n- **Budget Status**: For each budget category, show planned amount, actual spending, remaining balance, and percentage used\n- **Over-Budget Alerts**: Highlight any categories that have exceeded or are close to exceeding (>80%) their budget\n- **Under-Budget Categories**: Identify categories with significant unused budget\n- **Pace Analysis**: Based on the current day of the month, project whether each category will finish over or under budget at the current spending rate\n- **Recommendations**: Suggest specific adjustments for the remainder of the month to stay on track",
          },
        },
      ],
    })
  );

  server.registerPrompt(
    "spending-audit",
    {
      description:
        "Deep dive into spending patterns to uncover savings opportunities, lifestyle inflation, and spending habits",
    },
    async () => ({
      messages: [
        {
          role: "user" as const,
          content: {
            type: "text" as const,
            text: "Please perform a deep spending audit. Use these tools:\n\n1. **analyze_spending** - Analyze spending for the last 30 days with full category breakdown\n2. **detect_trends** - Identify spending trends over the last 6 months to spot increasing costs\n3. **detect_anomalies** - Find unusual transactions, duplicates, or suspicious charges\n4. **track_subscriptions** - Review all recurring payments and subscriptions\n\nProvide a thorough audit report with:\n- **Spending Summary**: Total spending, daily average, and comparison to previous periods\n- **Category Deep Dive**: For each major category, show total spent, transaction count, average transaction size, and top merchants\n- **Trend Analysis**: Categories where spending is increasing or decreasing over time, with percentage changes\n- **Subscription Review**: List all active subscriptions with monthly/annual costs and flag any that seem unused or redundant\n- **Anomaly Report**: Any duplicate charges, unusually large transactions, or unfamiliar merchants\n- **Savings Opportunities**: Specific, actionable recommendations to reduce spending, ranked by potential savings amount",
          },
        },
      ],
    })
  );

  server.registerPrompt(
    "net-worth-update",
    {
      description:
        "Track net worth changes, analyze asset and liability trends, and assess progress toward financial goals",
    },
    async () => ({
      messages: [
        {
          role: "user" as const,
          content: {
            type: "text" as const,
            text: "Please provide a net worth update and trend analysis. Use these tools:\n\n1. **get_accounts** - Get current account balances across all asset and liability accounts\n2. **get_account_history** - Check balance history for major accounts to see trends\n3. **get_financial_health_score** - Get the overall financial health assessment\n\nProvide a comprehensive net worth report with:\n- **Current Net Worth**: Total assets, total liabilities, and net worth\n- **Account Breakdown**: List each account with its current balance, grouped by type (checking, savings, investments, credit cards, loans)\n- **Changes**: Month-over-month and year-over-year net worth changes, both in dollar amount and percentage\n- **Asset Allocation**: How assets are distributed across account types (cash, investments, property, etc.)\n- **Debt Status**: Outstanding balances on all debt accounts with interest rates if available\n- **Trajectory**: Based on current trends, project net worth 3, 6, and 12 months from now\n- **Action Items**: Specific steps to accelerate net worth growth, such as debt payoff priorities or savings rate improvements",
          },
        },
      ],
    })
  );

  server.registerPrompt(
    "subscription-audit",
    {
      description:
        "Review all recurring payments and subscriptions to find forgotten services, price increases, and savings opportunities",
    },
    async () => ({
      messages: [
        {
          role: "user" as const,
          content: {
            type: "text" as const,
            text: "Please perform a thorough subscription and recurring payment audit. Use these tools:\n\n1. **track_subscriptions** - Get a complete analysis of all recurring payments including price changes and cost totals\n2. **detect_anomalies** - Check for any unusual changes in recurring charges\n3. **detect_trends** - Look at subscription-related spending trends over time\n\nProvide a detailed subscription audit with:\n- **Active Subscriptions**: List every recurring payment with name, amount, frequency (monthly/annual), and category\n- **Total Cost Summary**: Calculate total monthly and annual cost of all subscriptions combined\n- **Price Changes**: Highlight any subscriptions that have changed in price recently, showing old vs new amounts\n- **Potential Duplicates**: Flag any services that might overlap in functionality (e.g., multiple streaming services, multiple cloud storage)\n- **Usage Assessment**: Based on transaction frequency and amounts, flag subscriptions that might be forgotten or underused\n- **Cost Optimization**: Suggest specific subscriptions to cancel, downgrade, or switch to annual billing for savings, with estimated monthly and annual savings for each recommendation\n- **Year-over-Year Growth**: Show how total subscription costs have changed over the past year",
          },
        },
      ],
    })
  );
}
