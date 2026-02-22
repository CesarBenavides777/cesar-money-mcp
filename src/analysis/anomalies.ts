// ── Anomaly Detection ───────────────────────────────────────────────
// Detects unusual transactions: outlier amounts, potential duplicates,
// and first-time merchants.

import type { Transaction } from "./spending.js";

export interface Anomaly {
  type: "unusual_amount" | "duplicate" | "new_merchant" | "frequency_change";
  severity: "low" | "medium" | "high";
  description: string;
  transaction: {
    id: string;
    date: string;
    amount: number;
    merchant: string;
  };
}

export interface AnomalyOptions {
  /** Number of standard deviations for unusual-amount detection (default: 2) */
  stdDevThreshold?: number;
  /** Number of days within which same-merchant-same-amount is a duplicate (default: 3) */
  duplicateWindowDays?: number;
  /** Minimum transactions per merchant to compute stats (default: 3) */
  minTransactionsForStats?: number;
  /** Historical transactions used to build merchant baselines */
  historicalTransactions?: Transaction[];
}

/**
 * Detect anomalies across a set of transactions.
 *
 * When `historicalTransactions` is supplied, those are used to build
 * baselines while `transactions` contains the set to scan for anomalies.
 * If omitted, `transactions` is used for both purposes.
 */
export function detectAnomalies(
  transactions: Transaction[],
  options: AnomalyOptions = {},
): Anomaly[] {
  if (transactions.length === 0) return [];

  const stdDevThreshold = options.stdDevThreshold ?? 2;
  const duplicateWindowDays = options.duplicateWindowDays ?? 3;
  const minTxForStats = options.minTransactionsForStats ?? 3;

  const baseline = options.historicalTransactions ?? transactions;

  const anomalies: Anomaly[] = [];

  // ── 1. Build merchant statistics from baseline ────────────────────
  const merchantStats = buildMerchantStats(baseline);

  // ── 2. Unusual amounts ────────────────────────────────────────────
  for (const tx of transactions) {
    const stats = merchantStats.get(normalizeMerchant(tx.merchant));
    if (!stats || stats.count < minTxForStats) continue;

    const absAmount = Math.abs(tx.amount);
    const deviation = Math.abs(absAmount - stats.mean);

    if (stats.stdDev > 0 && deviation > stdDevThreshold * stats.stdDev) {
      const multiplier = deviation / stats.stdDev;
      const severity = severityFromMultiplier(multiplier);
      anomalies.push({
        type: "unusual_amount",
        severity,
        description:
          `Transaction of $${absAmount.toFixed(2)} at "${tx.merchant}" ` +
          `is ${multiplier.toFixed(1)} standard deviations from the average ` +
          `of $${stats.mean.toFixed(2)}.`,
        transaction: {
          id: tx.id,
          date: tx.date,
          amount: tx.amount,
          merchant: tx.merchant,
        },
      });
    }
  }

  // ── 3. Potential duplicates ───────────────────────────────────────
  const sorted = [...transactions].sort((a, b) => a.date.localeCompare(b.date));

  for (let i = 0; i < sorted.length; i++) {
    const tx = sorted[i]!;
    for (let j = i + 1; j < sorted.length; j++) {
      const other = sorted[j]!;

      // Once we're past the window, stop inner loop
      if (daysBetween(tx.date, other.date) > duplicateWindowDays) break;

      if (
        tx.id !== other.id &&
        normalizeMerchant(tx.merchant) === normalizeMerchant(other.merchant) &&
        tx.amount === other.amount
      ) {
        anomalies.push({
          type: "duplicate",
          severity: "medium",
          description:
            `Possible duplicate: $${Math.abs(tx.amount).toFixed(2)} at ` +
            `"${tx.merchant}" on ${tx.date} and ${other.date}.`,
          transaction: {
            id: other.id,
            date: other.date,
            amount: other.amount,
            merchant: other.merchant,
          },
        });
      }
    }
  }

  // ── 4. New merchants ──────────────────────────────────────────────
  const baselineMerchants = new Set<string>();
  if (options.historicalTransactions) {
    for (const tx of options.historicalTransactions) {
      baselineMerchants.add(normalizeMerchant(tx.merchant));
    }

    for (const tx of transactions) {
      const norm = normalizeMerchant(tx.merchant);
      if (!baselineMerchants.has(norm)) {
        anomalies.push({
          type: "new_merchant",
          severity: "low",
          description: `First-time merchant "${tx.merchant}" not seen in prior period.`,
          transaction: {
            id: tx.id,
            date: tx.date,
            amount: tx.amount,
            merchant: tx.merchant,
          },
        });
        // Mark as seen so we don't flag again within the same scan
        baselineMerchants.add(norm);
      }
    }
  }

  // Sort: high severity first, then by date descending
  anomalies.sort((a, b) => {
    const sevOrder = { high: 0, medium: 1, low: 2 };
    const sevDiff = sevOrder[a.severity] - sevOrder[b.severity];
    if (sevDiff !== 0) return sevDiff;
    return b.transaction.date.localeCompare(a.transaction.date);
  });

  return anomalies;
}

// ── Internal helpers ────────────────────────────────────────────────

interface MerchantStat {
  mean: number;
  stdDev: number;
  count: number;
}

function buildMerchantStats(
  transactions: Transaction[],
): Map<string, MerchantStat> {
  const buckets = new Map<string, number[]>();

  for (const tx of transactions) {
    const key = normalizeMerchant(tx.merchant);
    let amounts = buckets.get(key);
    if (!amounts) {
      amounts = [];
      buckets.set(key, amounts);
    }
    amounts.push(Math.abs(tx.amount));
  }

  const stats = new Map<string, MerchantStat>();

  for (const [key, amounts] of buckets) {
    const n = amounts.length;
    const mean = amounts.reduce((s, v) => s + v, 0) / n;

    let variance = 0;
    for (const a of amounts) {
      variance += (a - mean) ** 2;
    }
    variance = n > 1 ? variance / (n - 1) : 0; // sample variance

    stats.set(key, { mean, stdDev: Math.sqrt(variance), count: n });
  }

  return stats;
}

function normalizeMerchant(merchant: string): string {
  return merchant.trim().toLowerCase();
}

function daysBetween(a: string, b: string): number {
  const msPerDay = 86_400_000;
  const diff = Math.abs(new Date(b).getTime() - new Date(a).getTime());
  return Math.round(diff / msPerDay);
}

function severityFromMultiplier(multiplier: number): Anomaly["severity"] {
  if (multiplier >= 4) return "high";
  if (multiplier >= 3) return "medium";
  return "low";
}
