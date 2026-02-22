// ── Cash Flow Forecasting ───────────────────────────────────────────
// Projects account balances forward by combining recurring items with
// average discretionary spending and uncertainty bounds.

import type { Transaction } from "./spending.js";

export interface ForecastPoint {
  date: string; // "YYYY-MM-DD"
  projected: number;
  lower: number;
  upper: number;
}

export interface CashflowForecast {
  currentBalance: number;
  projectedBalance: number;
  forecastDays: number;
  dailyProjections: ForecastPoint[];
  recurringIncome: number;
  recurringExpenses: number;
  discretionaryAverage: number;
}

export interface Account {
  id: string;
  displayName: string;
  currentBalance: number;
  /** If true this account is included in net-worth but excluded from cashflow */
  isAsset?: boolean;
}

export interface RecurringItem {
  id: string;
  merchant: string;
  amount: number; // negative = expense, positive = income
  frequency: "weekly" | "biweekly" | "monthly" | "quarterly" | "annual";
  /** Next expected date "YYYY-MM-DD" */
  nextDate: string;
}

export interface ForecastOptions {
  /** Number of days to project (default: 30) */
  forecastDays?: number;
  /** Only include these account ids in balance. All if omitted. */
  accountIds?: string[];
  /** Historical transactions for discretionary average (last 90 days recommended) */
  transactions?: Transaction[];
  /** IDs of merchants that are recurring — used to separate discretionary */
  recurringMerchantIds?: Set<string>;
}

/**
 * Forecast future cash flow.
 *
 * @param accounts   Current account balances
 * @param transactions  Historical transactions to compute discretionary average
 * @param recurringItems  Known recurring income/expenses
 * @param options   Additional options
 */
export function forecastCashflow(
  accounts: Account[],
  transactions: Transaction[],
  recurringItems: RecurringItem[],
  options: ForecastOptions = {},
): CashflowForecast {
  const forecastDays = options.forecastDays ?? 30;

  // ── 1. Compute current balance ────────────────────────────────────
  const relevantAccounts = options.accountIds
    ? accounts.filter((a) => options.accountIds!.includes(a.id))
    : accounts.filter((a) => !a.isAsset);

  const currentBalance = relevantAccounts.reduce(
    (sum, a) => sum + a.currentBalance,
    0,
  );

  // ── 2. Map recurring items to daily amounts ───────────────────────
  const recurringIncome = recurringItems
    .filter((r) => r.amount > 0)
    .reduce((sum, r) => sum + dailyEquivalent(r.amount, r.frequency), 0);

  const recurringExpenses = recurringItems
    .filter((r) => r.amount < 0)
    .reduce((sum, r) => sum + Math.abs(dailyEquivalent(r.amount, r.frequency)), 0);

  // ── 3. Compute discretionary daily average ────────────────────────
  const recurringMerchantNorms = new Set<string>();
  for (const ri of recurringItems) {
    recurringMerchantNorms.add(ri.merchant.trim().toLowerCase());
  }
  if (options.recurringMerchantIds) {
    for (const id of options.recurringMerchantIds) {
      recurringMerchantNorms.add(id.trim().toLowerCase());
    }
  }

  const expenses = transactions.filter((tx) => tx.amount < 0);
  const discretionaryExpenses = expenses.filter(
    (tx) => !recurringMerchantNorms.has(tx.merchant.trim().toLowerCase()),
  );

  const { dailyAvg: discretionaryAverage, dailyStdDev } =
    computeDailyStats(discretionaryExpenses);

  // ── 4. Build recurring event calendar ─────────────────────────────
  const today = todayISO();
  const eventMap = buildRecurringEventMap(recurringItems, today, forecastDays);

  // ── 5. Day-by-day projection ──────────────────────────────────────
  const dailyProjections: ForecastPoint[] = [];
  let runningBalance = currentBalance;

  for (let d = 1; d <= forecastDays; d++) {
    const date = addDays(today, d);

    // Add any recurring events hitting this exact date
    const dayEvents = eventMap.get(date) ?? 0;
    const baseChange = dayEvents - discretionaryAverage;

    runningBalance += baseChange;

    // Confidence bounds widen over time (sqrt scaling)
    const uncertaintyFactor = Math.sqrt(d);
    const lower = runningBalance - dailyStdDev * uncertaintyFactor;
    const upper = runningBalance + dailyStdDev * uncertaintyFactor;

    dailyProjections.push({
      date,
      projected: round(runningBalance),
      lower: round(lower),
      upper: round(upper),
    });
  }

  const projectedBalance =
    dailyProjections.length > 0
      ? dailyProjections[dailyProjections.length - 1]!.projected
      : currentBalance;

  return {
    currentBalance: round(currentBalance),
    projectedBalance: round(projectedBalance),
    forecastDays,
    dailyProjections,
    recurringIncome: round(recurringIncome),
    recurringExpenses: round(recurringExpenses),
    discretionaryAverage: round(discretionaryAverage),
  };
}

// ── Helpers ─────────────────────────────────────────────────────────

function dailyEquivalent(
  amount: number,
  frequency: RecurringItem["frequency"],
): number {
  switch (frequency) {
    case "weekly":
      return amount / 7;
    case "biweekly":
      return amount / 14;
    case "monthly":
      return amount / 30;
    case "quarterly":
      return amount / 91;
    case "annual":
      return amount / 365;
  }
}

/**
 * Given a list of expense transactions, group them by date, compute
 * the daily average spending and its standard deviation.
 */
function computeDailyStats(expenses: Transaction[]): {
  dailyAvg: number;
  dailyStdDev: number;
} {
  if (expenses.length === 0) return { dailyAvg: 0, dailyStdDev: 0 };

  // Aggregate spending per day
  const dayTotals = new Map<string, number>();
  for (const tx of expenses) {
    const current = dayTotals.get(tx.date) ?? 0;
    dayTotals.set(tx.date, current + Math.abs(tx.amount));
  }

  const values = [...dayTotals.values()];
  if (values.length === 0) return { dailyAvg: 0, dailyStdDev: 0 };

  const n = values.length;
  const mean = values.reduce((s, v) => s + v, 0) / n;

  let variance = 0;
  for (const v of values) {
    variance += (v - mean) ** 2;
  }
  variance = n > 1 ? variance / (n - 1) : 0;

  return { dailyAvg: mean, dailyStdDev: Math.sqrt(variance) };
}

/**
 * Build a map from date string to the sum of recurring amounts on that day.
 * Generates occurrences of each recurring item within the forecast window.
 */
function buildRecurringEventMap(
  items: RecurringItem[],
  startDate: string,
  days: number,
): Map<string, number> {
  const map = new Map<string, number>();
  const endDate = addDays(startDate, days);

  for (const item of items) {
    const occurrences = generateOccurrences(item, startDate, endDate);
    for (const date of occurrences) {
      const current = map.get(date) ?? 0;
      map.set(date, current + item.amount);
    }
  }

  return map;
}

/**
 * Generate all occurrence dates for a recurring item within [start, end].
 */
function generateOccurrences(
  item: RecurringItem,
  start: string,
  end: string,
): string[] {
  const dates: string[] = [];
  let current = item.nextDate;

  // If nextDate is before start, advance it
  while (current < start) {
    current = advanceByFrequency(current, item.frequency);
  }

  while (current <= end) {
    dates.push(current);
    current = advanceByFrequency(current, item.frequency);
  }

  return dates;
}

function advanceByFrequency(
  dateStr: string,
  frequency: RecurringItem["frequency"],
): string {
  const d = new Date(dateStr + "T00:00:00");
  switch (frequency) {
    case "weekly":
      d.setDate(d.getDate() + 7);
      break;
    case "biweekly":
      d.setDate(d.getDate() + 14);
      break;
    case "monthly":
      d.setMonth(d.getMonth() + 1);
      break;
    case "quarterly":
      d.setMonth(d.getMonth() + 3);
      break;
    case "annual":
      d.setFullYear(d.getFullYear() + 1);
      break;
  }
  return formatDate(d);
}

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

function addDays(dateStr: string, days: number): string {
  const d = new Date(dateStr + "T00:00:00");
  d.setDate(d.getDate() + days);
  return formatDate(d);
}

function formatDate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function round(n: number): number {
  return Math.round(n * 100) / 100;
}
