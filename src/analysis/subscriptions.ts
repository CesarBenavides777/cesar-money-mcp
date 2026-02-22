// ── Subscription Tracking ───────────────────────────────────────────
// Detects recurring payment patterns, estimates frequency, computes
// annual cost, and flags price changes.

export interface Subscription {
  merchant: string;
  amount: number;
  frequency: "weekly" | "monthly" | "quarterly" | "annual";
  nextExpected: string; // "YYYY-MM-DD"
  annualCost: number;
  priceHistory: { date: string; amount: number }[];
  priceChanged: boolean;
}

export interface SubscriptionSummary {
  totalMonthly: number;
  totalAnnual: number;
  subscriptions: Subscription[];
  recentChanges: Subscription[];
}

export interface RecurringTransaction {
  id: string;
  date: string; // "YYYY-MM-DD"
  amount: number; // negative = expense
  merchant: string;
}

export interface SubscriptionOptions {
  /** Tolerance in days when detecting frequency gaps (default: 5) */
  dayTolerance?: number;
  /** Percentage threshold for flagging price changes (default: 1) */
  priceChangeThreshold?: number;
}

/**
 * Analyse recurring transactions to build a subscription summary.
 *
 * Expects expense transactions (amount < 0) that are already identified
 * as recurring by Monarch. Groups by normalized merchant, detects
 * frequency from inter-payment intervals, and flags price changes.
 */
export function analyzeSubscriptions(
  recurringTransactions: RecurringTransaction[],
  options: SubscriptionOptions = {},
): SubscriptionSummary {
  const dayTolerance = options.dayTolerance ?? 5;
  const priceChangeThreshold = options.priceChangeThreshold ?? 1;

  if (recurringTransactions.length === 0) {
    return {
      totalMonthly: 0,
      totalAnnual: 0,
      subscriptions: [],
      recentChanges: [],
    };
  }

  // ── Group by merchant ─────────────────────────────────────────────
  const merchantGroups = new Map<string, RecurringTransaction[]>();

  for (const tx of recurringTransactions) {
    const key = normalizeMerchant(tx.merchant);
    let group = merchantGroups.get(key);
    if (!group) {
      group = [];
      merchantGroups.set(key, group);
    }
    group.push(tx);
  }

  // ── Analyse each merchant group ───────────────────────────────────
  const subscriptions: Subscription[] = [];

  for (const [, group] of merchantGroups) {
    // Sort chronologically
    const sorted = [...group].sort((a, b) => a.date.localeCompare(b.date));

    // Use the display name from the most recent transaction
    const displayMerchant = sorted[sorted.length - 1]!.merchant;

    // Build price history (absolute amounts)
    const priceHistory = sorted.map((tx) => ({
      date: tx.date,
      amount: round(Math.abs(tx.amount)),
    }));

    // Detect frequency from intervals
    const frequency = detectFrequency(sorted, dayTolerance);

    // Latest amount
    const latestAmount = round(Math.abs(sorted[sorted.length - 1]!.amount));

    // Annual cost based on frequency
    const annualCost = round(annualMultiplier(frequency) * latestAmount);

    // Detect price change: compare latest two distinct amounts
    const priceChanged = hasPriceChanged(priceHistory, priceChangeThreshold);

    // Estimate next expected date
    const lastDate = sorted[sorted.length - 1]!.date;
    const nextExpected = advanceDate(lastDate, frequency);

    subscriptions.push({
      merchant: displayMerchant,
      amount: latestAmount,
      frequency,
      nextExpected,
      annualCost,
      priceHistory,
      priceChanged,
    });
  }

  // Sort by annual cost descending
  subscriptions.sort((a, b) => b.annualCost - a.annualCost);

  // ── Totals ────────────────────────────────────────────────────────
  const totalAnnual = round(
    subscriptions.reduce((s, sub) => s + sub.annualCost, 0),
  );
  const totalMonthly = round(totalAnnual / 12);

  const recentChanges = subscriptions.filter((s) => s.priceChanged);

  return { totalMonthly, totalAnnual, subscriptions, recentChanges };
}

// ── Helpers ─────────────────────────────────────────────────────────

function detectFrequency(
  sorted: RecurringTransaction[],
  tolerance: number,
): Subscription["frequency"] {
  if (sorted.length < 2) return "monthly"; // default assumption

  // Compute average interval in days
  const intervals: number[] = [];
  for (let i = 1; i < sorted.length; i++) {
    intervals.push(daysBetween(sorted[i - 1]!.date, sorted[i]!.date));
  }

  const avgInterval =
    intervals.reduce((s, v) => s + v, 0) / intervals.length;

  // Match to known frequency
  if (isWithin(avgInterval, 7, tolerance)) return "weekly";
  if (isWithin(avgInterval, 30, tolerance + 3)) return "monthly"; // wider window for month variance
  if (isWithin(avgInterval, 14, tolerance)) return "weekly"; // biweekly detected as weekly is close but let's check 91
  if (isWithin(avgInterval, 91, tolerance + 10)) return "quarterly";
  if (isWithin(avgInterval, 365, tolerance + 30)) return "annual";

  // Fallback: pick closest
  const candidates: Array<{ freq: Subscription["frequency"]; days: number }> = [
    { freq: "weekly", days: 7 },
    { freq: "monthly", days: 30 },
    { freq: "quarterly", days: 91 },
    { freq: "annual", days: 365 },
  ];

  let best = candidates[0]!;
  for (const c of candidates) {
    if (Math.abs(avgInterval - c.days) < Math.abs(avgInterval - best.days)) {
      best = c;
    }
  }

  return best.freq;
}

function isWithin(value: number, target: number, tolerance: number): boolean {
  return Math.abs(value - target) <= tolerance;
}

function annualMultiplier(freq: Subscription["frequency"]): number {
  switch (freq) {
    case "weekly":
      return 52;
    case "monthly":
      return 12;
    case "quarterly":
      return 4;
    case "annual":
      return 1;
  }
}

function hasPriceChanged(
  history: { date: string; amount: number }[],
  thresholdPercent: number,
): boolean {
  if (history.length < 2) return false;

  // Compare the last amount to the second-to-last
  const latest = history[history.length - 1]!.amount;
  const previous = history[history.length - 2]!.amount;

  if (previous === 0) return latest !== 0;

  const changePct = Math.abs(((latest - previous) / previous) * 100);
  return changePct >= thresholdPercent;
}

function advanceDate(dateStr: string, frequency: Subscription["frequency"]): string {
  const d = new Date(dateStr + "T00:00:00");
  switch (frequency) {
    case "weekly":
      d.setDate(d.getDate() + 7);
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

function daysBetween(a: string, b: string): number {
  const msPerDay = 86_400_000;
  return Math.round(
    Math.abs(new Date(b).getTime() - new Date(a).getTime()) / msPerDay,
  );
}

function normalizeMerchant(merchant: string): string {
  return merchant.trim().toLowerCase();
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
