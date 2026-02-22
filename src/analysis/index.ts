// ── Analysis Engine ──────────────────────────────────────────────────
// Barrel export for all analysis modules.
// Pure functions only — no MCP or API dependencies.

export {
  analyzeSpending,
  type SpendingBreakdown,
  type SpendingAnalysis,
  type SpendingOptions,
  type Transaction,
} from "./spending.js";

export {
  detectTrends,
  type TrendPoint,
  type Trend,
  type TrendOptions,
} from "./trends.js";

export {
  detectAnomalies,
  type Anomaly,
  type AnomalyOptions,
} from "./anomalies.js";

export {
  forecastCashflow,
  type ForecastPoint,
  type CashflowForecast,
  type Account,
  type RecurringItem,
  type ForecastOptions,
} from "./forecasting.js";

export {
  analyzeSubscriptions,
  type Subscription,
  type SubscriptionSummary,
  type RecurringTransaction,
  type SubscriptionOptions,
} from "./subscriptions.js";

export {
  calculateHealthScore,
  type HealthScore,
  type ComponentScore,
  type HealthAccount,
  type BudgetItem,
  type NetWorthPoint,
  type HealthData,
} from "./health.js";
