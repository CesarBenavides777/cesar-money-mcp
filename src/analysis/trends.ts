// ── Trend Detection ─────────────────────────────────────────────────
// Groups transactions by month + category and uses linear regression
// to determine whether spending is increasing, decreasing, or stable.

import type { Transaction } from "./spending.js";

export interface TrendPoint {
  period: string; // "YYYY-MM"
  amount: number;
}

export interface Trend {
  category: string;
  direction: "increasing" | "decreasing" | "stable";
  changePercent: number;
  dataPoints: TrendPoint[];
}

export interface TrendOptions {
  /** Minimum number of months of data required to compute a trend (default: 3) */
  minMonths?: number;
  /** Percentage change threshold below which direction is "stable" (default: 5) */
  stableThreshold?: number;
  /** Restrict analysis to these categories. All if omitted. */
  categories?: string[];
  /** ISO date lower bound */
  startDate?: string;
  /** ISO date upper bound */
  endDate?: string;
}

/**
 * Detect spending trends across categories over time.
 *
 * Only expenses (`amount < 0`) are considered.
 * Returns one `Trend` per category that has at least `minMonths` of data.
 */
export function detectTrends(
  transactions: Transaction[],
  options: TrendOptions = {},
): Trend[] {
  const minMonths = options.minMonths ?? 3;
  const stableThreshold = options.stableThreshold ?? 5;

  // ── Filter ────────────────────────────────────────────────────────
  let filtered = transactions.filter((tx) => tx.amount < 0);
  if (options.startDate) {
    filtered = filtered.filter((tx) => tx.date >= options.startDate!);
  }
  if (options.endDate) {
    filtered = filtered.filter((tx) => tx.date <= options.endDate!);
  }
  if (options.categories && options.categories.length > 0) {
    const catSet = new Set(options.categories);
    filtered = filtered.filter((tx) => catSet.has(tx.category?.name ?? "Uncategorized"));
  }

  if (filtered.length === 0) return [];

  // ── Group by category -> month -> total ───────────────────────────
  const categoryMonths = new Map<string, Map<string, number>>();

  for (const tx of filtered) {
    const cat = tx.category?.name || "Uncategorized";
    const month = tx.date.slice(0, 7); // "YYYY-MM"

    let monthMap = categoryMonths.get(cat);
    if (!monthMap) {
      monthMap = new Map<string, number>();
      categoryMonths.set(cat, monthMap);
    }

    const current = monthMap.get(month) ?? 0;
    monthMap.set(month, current + Math.abs(tx.amount));
  }

  // ── Compute trends ────────────────────────────────────────────────
  const trends: Trend[] = [];

  for (const [category, monthMap] of categoryMonths) {
    // Build sorted data points
    const dataPoints: TrendPoint[] = [];
    for (const [period, amount] of monthMap) {
      dataPoints.push({ period, amount: round(amount) });
    }
    dataPoints.sort((a, b) => a.period.localeCompare(b.period));

    if (dataPoints.length < minMonths) continue;

    // ── Linear regression on sequential indices ─────────────────────
    const n = dataPoints.length;
    const xs = dataPoints.map((_, i) => i);
    const ys = dataPoints.map((dp) => dp.amount);

    const slope = linearRegressionSlope(xs, ys);

    // Compute percentage change relative to the first fitted value
    // fitted_first = intercept, fitted_last = intercept + slope*(n-1)
    // We only need the ratio: total_change / first_value
    const meanY = ys.reduce((s, v) => s + v, 0) / n;
    const firstFitted = meanY - slope * ((n - 1) / 2); // intercept via mean centering
    const totalChange = slope * (n - 1);
    const changePercent =
      firstFitted !== 0 ? round((totalChange / Math.abs(firstFitted)) * 100) : 0;

    let direction: Trend["direction"];
    if (Math.abs(changePercent) < stableThreshold) {
      direction = "stable";
    } else if (changePercent > 0) {
      direction = "increasing";
    } else {
      direction = "decreasing";
    }

    trends.push({ category, direction, changePercent, dataPoints });
  }

  // Sort by absolute change descending — most dramatic trends first
  trends.sort((a, b) => Math.abs(b.changePercent) - Math.abs(a.changePercent));

  return trends;
}

// ── Helpers ─────────────────────────────────────────────────────────

/**
 * Ordinary least-squares slope for paired (x, y) arrays.
 * Returns 0 when input is empty or has no variance.
 */
function linearRegressionSlope(xs: number[], ys: number[]): number {
  const n = xs.length;
  if (n < 2) return 0;

  let sumX = 0;
  let sumY = 0;
  let sumXY = 0;
  let sumXX = 0;

  for (let i = 0; i < n; i++) {
    const x = xs[i]!;
    const y = ys[i]!;
    sumX += x;
    sumY += y;
    sumXY += x * y;
    sumXX += x * x;
  }

  const denominator = n * sumXX - sumX * sumX;
  if (denominator === 0) return 0;

  return (n * sumXY - sumX * sumY) / denominator;
}

function round(n: number): number {
  return Math.round(n * 100) / 100;
}
