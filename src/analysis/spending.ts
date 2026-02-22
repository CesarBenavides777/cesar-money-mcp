// ── Spending Analysis ───────────────────────────────────────────────
// Pure functions that compute spending breakdowns from raw transactions.

export interface SpendingBreakdown {
  category: string;
  amount: number;
  percentage: number;
  transactionCount: number;
}

export interface SpendingAnalysis {
  period: { start: string; end: string };
  totalSpending: number;
  totalIncome: number;
  netCashflow: number;
  topCategories: SpendingBreakdown[];
  dailyAverage: number;
  comparisonToPriorPeriod?: {
    spendingChange: number;
    spendingChangePercent: number;
  };
}

export interface Transaction {
  id: string;
  date: string; // "YYYY-MM-DD"
  amount: number; // negative = expense, positive = income
  merchant: string;
  category: { name: string };
}

export interface SpendingOptions {
  /** ISO date string for period start (inclusive). Derived from data if omitted. */
  startDate?: string;
  /** ISO date string for period end (inclusive). Derived from data if omitted. */
  endDate?: string;
  /** Maximum number of top categories to return (default: 10) */
  topN?: number;
  /** Prior-period transactions for comparison */
  priorPeriodTransactions?: Transaction[];
}

/**
 * Analyse spending across a set of transactions.
 *
 * Expenses are transactions with `amount < 0`.
 * Income is transactions with `amount > 0`.
 */
export function analyzeSpending(
  transactions: Transaction[],
  options: SpendingOptions = {},
): SpendingAnalysis {
  const topN = options.topN ?? 10;

  // ── Filter to the requested period ────────────────────────────────
  const filtered = filterByPeriod(
    transactions,
    options.startDate,
    options.endDate,
  );

  // ── Derive period bounds from data (or options) ───────────────────
  const period = derivePeriod(filtered, options.startDate, options.endDate);

  // ── Aggregate totals ──────────────────────────────────────────────
  let totalSpending = 0;
  let totalIncome = 0;

  const categoryMap = new Map<
    string,
    { amount: number; transactionCount: number }
  >();

  for (const tx of filtered) {
    if (tx.amount < 0) {
      totalSpending += Math.abs(tx.amount);
    } else {
      totalIncome += tx.amount;
    }

    // Category aggregation — only expenses contribute
    if (tx.amount < 0) {
      const cat = tx.category.name || "Uncategorized";
      const existing = categoryMap.get(cat);
      if (existing) {
        existing.amount += Math.abs(tx.amount);
        existing.transactionCount += 1;
      } else {
        categoryMap.set(cat, {
          amount: Math.abs(tx.amount),
          transactionCount: 1,
        });
      }
    }
  }

  // ── Build sorted breakdown ────────────────────────────────────────
  const breakdowns: SpendingBreakdown[] = [];
  for (const [category, data] of categoryMap) {
    breakdowns.push({
      category,
      amount: round(data.amount),
      percentage: totalSpending > 0 ? round((data.amount / totalSpending) * 100) : 0,
      transactionCount: data.transactionCount,
    });
  }

  breakdowns.sort((a, b) => b.amount - a.amount);
  const topCategories = breakdowns.slice(0, topN);

  // ── Daily average ─────────────────────────────────────────────────
  const days = daysBetween(period.start, period.end);
  const dailyAverage = days > 0 ? round(totalSpending / days) : round(totalSpending);

  // ── Prior period comparison ───────────────────────────────────────
  let comparisonToPriorPeriod: SpendingAnalysis["comparisonToPriorPeriod"];
  if (options.priorPeriodTransactions && options.priorPeriodTransactions.length > 0) {
    let priorSpending = 0;
    for (const tx of options.priorPeriodTransactions) {
      if (tx.amount < 0) {
        priorSpending += Math.abs(tx.amount);
      }
    }
    const spendingChange = round(totalSpending - priorSpending);
    const spendingChangePercent =
      priorSpending > 0 ? round((spendingChange / priorSpending) * 100) : 0;

    comparisonToPriorPeriod = { spendingChange, spendingChangePercent };
  }

  return {
    period,
    totalSpending: round(totalSpending),
    totalIncome: round(totalIncome),
    netCashflow: round(totalIncome - totalSpending),
    topCategories,
    dailyAverage,
    comparisonToPriorPeriod,
  };
}

// ── Helpers ─────────────────────────────────────────────────────────

function filterByPeriod(
  transactions: Transaction[],
  start?: string,
  end?: string,
): Transaction[] {
  if (!start && !end) return transactions;
  return transactions.filter((tx) => {
    if (start && tx.date < start) return false;
    if (end && tx.date > end) return false;
    return true;
  });
}

function derivePeriod(
  transactions: Transaction[],
  start?: string,
  end?: string,
): { start: string; end: string } {
  if (start && end) return { start, end };

  if (transactions.length === 0) {
    const today = new Date().toISOString().slice(0, 10);
    return { start: start ?? today, end: end ?? today };
  }

  let minDate = transactions[0]!.date;
  let maxDate = transactions[0]!.date;

  for (const tx of transactions) {
    if (tx.date < minDate) minDate = tx.date;
    if (tx.date > maxDate) maxDate = tx.date;
  }

  return { start: start ?? minDate, end: end ?? maxDate };
}

function daysBetween(a: string, b: string): number {
  const msPerDay = 86_400_000;
  const diff = new Date(b).getTime() - new Date(a).getTime();
  return Math.max(1, Math.round(diff / msPerDay) + 1); // inclusive
}

function round(n: number): number {
  return Math.round(n * 100) / 100;
}
