// ── Financial Health Score ───────────────────────────────────────────
// Computes a composite 0-100 score from five components: savings rate,
// debt-to-asset ratio, emergency fund adequacy, budget adherence, and
// net-worth trend.

import type { Transaction } from "./spending.js";

export interface HealthScore {
  overall: number; // 0-100
  components: {
    savingsRate: ComponentScore;
    debtRatio: ComponentScore;
    emergencyFund: ComponentScore;
    budgetAdherence: ComponentScore;
    netWorthTrend: ComponentScore;
  };
  recommendations: string[];
}

export interface ComponentScore {
  score: number; // 0-100
  value: number; // the raw metric
  description: string;
}

export interface HealthAccount {
  id: string;
  displayName: string;
  currentBalance: number;
  type: "depository" | "investment" | "credit" | "loan" | "mortgage" | "other";
}

export interface BudgetItem {
  category: string;
  budgeted: number; // positive amount
  actual: number; // positive = spent
}

export interface NetWorthPoint {
  date: string; // "YYYY-MM-DD"
  netWorth: number;
}

export interface HealthData {
  accounts: HealthAccount[];
  /** Recent transactions (e.g. last 3-6 months) */
  transactions: Transaction[];
  /** Current month's budget items */
  budgets: BudgetItem[];
  /** Historical net-worth snapshots (monthly) */
  netWorthHistory: NetWorthPoint[];
  /** Desired months of expenses for emergency fund (default: 6) */
  emergencyFundMonths?: number;
}

// ── Component weights (must sum to 1) ───────────────────────────────
const WEIGHTS = {
  savingsRate: 0.25,
  debtRatio: 0.2,
  emergencyFund: 0.2,
  budgetAdherence: 0.2,
  netWorthTrend: 0.15,
} as const;

/**
 * Calculate a composite financial health score.
 *
 * Each component yields a 0-100 sub-score. The overall score is a
 * weighted average. Missing data gracefully degrades: a component with
 * no data returns a neutral 50.
 */
export function calculateHealthScore(data: HealthData): HealthScore {
  const savingsRate = scoreSavingsRate(data.transactions);
  const debtRatio = scoreDebtRatio(data.accounts);
  const emergencyFund = scoreEmergencyFund(
    data.accounts,
    data.transactions,
    data.emergencyFundMonths ?? 6,
  );
  const budgetAdherence = scoreBudgetAdherence(data.budgets);
  const netWorthTrend = scoreNetWorthTrend(data.netWorthHistory);

  const overall = round(
    savingsRate.score * WEIGHTS.savingsRate +
      debtRatio.score * WEIGHTS.debtRatio +
      emergencyFund.score * WEIGHTS.emergencyFund +
      budgetAdherence.score * WEIGHTS.budgetAdherence +
      netWorthTrend.score * WEIGHTS.netWorthTrend,
  );

  const recommendations = generateRecommendations({
    savingsRate,
    debtRatio,
    emergencyFund,
    budgetAdherence,
    netWorthTrend,
  });

  return {
    overall: clamp(overall, 0, 100),
    components: {
      savingsRate,
      debtRatio,
      emergencyFund,
      budgetAdherence,
      netWorthTrend,
    },
    recommendations,
  };
}

// ── Component scorers ───────────────────────────────────────────────

/**
 * Savings rate = (income - spending) / income.
 * 20 %+ is excellent (100), 0% or negative is 0.
 */
function scoreSavingsRate(transactions: Transaction[]): ComponentScore {
  if (transactions.length === 0) {
    return { score: 50, value: 0, description: "No transaction data available." };
  }

  let income = 0;
  let spending = 0;
  for (const tx of transactions) {
    if (tx.amount > 0) income += tx.amount;
    else spending += Math.abs(tx.amount);
  }

  if (income === 0) {
    return {
      score: 0,
      value: 0,
      description: "No income detected in the period.",
    };
  }

  const rate = (income - spending) / income;
  const value = round(rate * 100); // as percentage
  const score = clamp(round(linearScale(rate, -0.1, 0.25, 0, 100)), 0, 100);

  let description: string;
  if (value >= 20) {
    description = `Excellent savings rate of ${value}%. You are saving well above the recommended 20%.`;
  } else if (value >= 10) {
    description = `Good savings rate of ${value}%. Aim for 20% or more for faster wealth building.`;
  } else if (value >= 0) {
    description = `Savings rate of ${value}%. Try to increase this to at least 10-20% of income.`;
  } else {
    description = `Negative savings rate of ${value}%. Spending exceeds income.`;
  }

  return { score, value, description };
}

/**
 * Debt-to-asset ratio. Lower is better.
 * 0% = 100, 100%+ = 0.
 */
function scoreDebtRatio(accounts: HealthAccount[]): ComponentScore {
  if (accounts.length === 0) {
    return { score: 50, value: 0, description: "No account data available." };
  }

  let assets = 0;
  let debts = 0;

  for (const acc of accounts) {
    if (acc.type === "credit" || acc.type === "loan" || acc.type === "mortgage") {
      debts += Math.abs(acc.currentBalance);
    } else {
      assets += Math.max(0, acc.currentBalance);
    }
  }

  if (assets === 0 && debts === 0) {
    return { score: 50, value: 0, description: "No balances detected." };
  }

  const ratio = assets > 0 ? debts / assets : (debts > 0 ? 1 : 0);
  const value = round(ratio * 100);
  const score = clamp(round(linearScale(ratio, 1, 0, 0, 100)), 0, 100);

  let description: string;
  if (value <= 20) {
    description = `Low debt-to-asset ratio of ${value}%. Your debts are well-managed.`;
  } else if (value <= 50) {
    description = `Moderate debt-to-asset ratio of ${value}%. Consider paying down high-interest debt.`;
  } else {
    description = `High debt-to-asset ratio of ${value}%. Prioritize debt reduction.`;
  }

  return { score, value, description };
}

/**
 * Emergency fund adequacy: liquid savings / monthly expenses.
 * 6+ months = 100, 0 months = 0.
 */
function scoreEmergencyFund(
  accounts: HealthAccount[],
  transactions: Transaction[],
  targetMonths: number,
): ComponentScore {
  // Liquid savings = depository balances
  const liquid = accounts
    .filter((a) => a.type === "depository")
    .reduce((s, a) => s + Math.max(0, a.currentBalance), 0);

  // Average monthly expenses
  const expenses = transactions.filter((tx) => tx.amount < 0);
  if (expenses.length === 0) {
    return {
      score: liquid > 0 ? 75 : 50,
      value: 0,
      description: liquid > 0
        ? "Unable to compute monthly expenses. You have liquid savings."
        : "No expense or savings data available.",
    };
  }

  const totalExpenses = expenses.reduce((s, tx) => s + Math.abs(tx.amount), 0);

  // Estimate months covered by the data
  const dates = expenses.map((tx) => tx.date).sort();
  const firstDate = dates[0]!;
  const lastDate = dates[dates.length - 1]!;
  const daysSpanned = Math.max(
    1,
    daysBetween(firstDate, lastDate) + 1,
  );
  const monthsSpanned = daysSpanned / 30;
  const monthlyExpenses = totalExpenses / monthsSpanned;

  if (monthlyExpenses === 0) {
    return { score: 100, value: 0, description: "No expenses detected." };
  }

  const monthsCovered = liquid / monthlyExpenses;
  const value = round(monthsCovered);
  const score = clamp(
    round(linearScale(monthsCovered, 0, targetMonths, 0, 100)),
    0,
    100,
  );

  let description: string;
  if (monthsCovered >= targetMonths) {
    description = `Emergency fund covers ${value} months of expenses, meeting the ${targetMonths}-month target.`;
  } else if (monthsCovered >= 3) {
    description = `Emergency fund covers ${value} months. Aim for ${targetMonths} months.`;
  } else if (monthsCovered >= 1) {
    description = `Emergency fund only covers ${value} months. Build this to ${targetMonths} months.`;
  } else {
    description = `Emergency fund covers less than 1 month of expenses. This is a priority area.`;
  }

  return { score, value, description };
}

/**
 * Budget adherence: percentage of categories at or under budget.
 * 100% adherence = 100, 0% = 0.
 */
function scoreBudgetAdherence(budgets: BudgetItem[]): ComponentScore {
  if (budgets.length === 0) {
    return {
      score: 50,
      value: 0,
      description: "No budget data available. Set up budgets for better tracking.",
    };
  }

  let onBudgetCount = 0;
  let totalOverspend = 0;
  let totalBudgeted = 0;

  for (const b of budgets) {
    totalBudgeted += b.budgeted;
    if (b.actual <= b.budgeted) {
      onBudgetCount += 1;
    } else {
      totalOverspend += b.actual - b.budgeted;
    }
  }

  const adherenceRate = onBudgetCount / budgets.length;
  const value = round(adherenceRate * 100);
  const score = clamp(round(adherenceRate * 100), 0, 100);

  const overspendPct =
    totalBudgeted > 0 ? round((totalOverspend / totalBudgeted) * 100) : 0;

  let description: string;
  if (value >= 90) {
    description = `Excellent budget adherence at ${value}%. You are staying within budget in nearly all categories.`;
  } else if (value >= 70) {
    description = `Good budget adherence at ${value}%. Total overspend across categories is ${overspendPct}% of budget.`;
  } else {
    description = `Budget adherence is ${value}%. Total overspend is ${overspendPct}% of budget. Review over-budget categories.`;
  }

  return { score, value, description };
}

/**
 * Net-worth trend: positive slope is good, negative is bad.
 * Uses the percentage change from first to last data point.
 */
function scoreNetWorthTrend(history: NetWorthPoint[]): ComponentScore {
  if (history.length < 2) {
    return {
      score: 50,
      value: 0,
      description: "Insufficient net-worth history for trend analysis.",
    };
  }

  const sorted = [...history].sort((a, b) => a.date.localeCompare(b.date));
  const first = sorted[0]!.netWorth;
  const last = sorted[sorted.length - 1]!.netWorth;

  // Monthly change rate
  const months = Math.max(1, sorted.length - 1);
  const totalChange = last - first;
  const monthlyChange = totalChange / months;

  // Percentage change from baseline (use absolute first to avoid sign issues)
  const changePct =
    first !== 0 ? round((totalChange / Math.abs(first)) * 100) : (totalChange > 0 ? 100 : 0);

  const value = round(changePct);

  // Score: -20% or worse = 0, +20% or better = 100
  const score = clamp(round(linearScale(changePct, -20, 20, 0, 100)), 0, 100);

  let description: string;
  if (changePct > 5) {
    description = `Net worth is trending up ${value}% (${monthlyChange >= 0 ? "+" : ""}$${round(monthlyChange).toLocaleString()}/month). Great progress.`;
  } else if (changePct >= -5) {
    description = `Net worth is relatively stable (${value}% change). Look for ways to grow.`;
  } else {
    description = `Net worth has declined ${value}%. Investigate and address the trend.`;
  }

  return { score, value, description };
}

// ── Recommendations ─────────────────────────────────────────────────

function generateRecommendations(components: HealthScore["components"]): string[] {
  const recs: string[] = [];

  if (components.savingsRate.score < 50) {
    recs.push(
      "Increase your savings rate by reducing discretionary spending or finding additional income sources.",
    );
  }

  if (components.debtRatio.score < 50) {
    recs.push(
      "Focus on paying down high-interest debt. Consider the avalanche or snowball method.",
    );
  }

  if (components.emergencyFund.score < 50) {
    recs.push(
      "Build your emergency fund to cover at least 3-6 months of expenses in a high-yield savings account.",
    );
  }

  if (components.budgetAdherence.score < 70) {
    recs.push(
      "Review budget categories where you are consistently overspending and adjust either spending or budget amounts.",
    );
  }

  if (components.netWorthTrend.score < 50) {
    recs.push(
      "Your net worth is declining. Review large expenses, asset values, and debt balances.",
    );
  }

  if (recs.length === 0) {
    recs.push(
      "Your finances are in good shape. Consider increasing investment contributions for long-term growth.",
    );
  }

  return recs;
}

// ── Utility ─────────────────────────────────────────────────────────

/**
 * Linearly map a value from [inMin, inMax] to [outMin, outMax].
 */
function linearScale(
  value: number,
  inMin: number,
  inMax: number,
  outMin: number,
  outMax: number,
): number {
  if (inMax === inMin) return (outMin + outMax) / 2;
  return outMin + ((value - inMin) / (inMax - inMin)) * (outMax - outMin);
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function daysBetween(a: string, b: string): number {
  const msPerDay = 86_400_000;
  return Math.round(
    Math.abs(new Date(b).getTime() - new Date(a).getTime()) / msPerDay,
  );
}

function round(n: number): number {
  return Math.round(n * 100) / 100;
}
