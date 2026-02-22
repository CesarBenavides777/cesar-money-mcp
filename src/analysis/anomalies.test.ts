import { describe, expect, test } from "bun:test";
import { detectAnomalies, type Anomaly } from "./anomalies.js";
import type { Transaction } from "./spending.js";

function tx(overrides: Partial<Transaction> = {}): Transaction {
  return {
    id: overrides.id ?? "tx-1",
    date: overrides.date ?? "2025-01-15",
    amount: overrides.amount ?? -50,
    merchant: overrides.merchant ?? "Coffee Shop",
    category: overrides.category ?? { name: "Food" },
  };
}

describe("detectAnomalies", () => {
  test("returns empty array for empty input", () => {
    expect(detectAnomalies([])).toEqual([]);
  });

  test("detects unusually large transactions", () => {
    // Build baseline: 10 transactions at ~$10, then one at $200
    const baseline: Transaction[] = [];
    for (let i = 0; i < 10; i++) {
      baseline.push(
        tx({ id: `b-${i}`, amount: -(9 + Math.random() * 2), merchant: "Coffee Shop" })
      );
    }
    const outlier = tx({ id: "outlier", amount: -200, merchant: "Coffee Shop" });
    const all = [...baseline, outlier];

    const anomalies = detectAnomalies(all);
    const unusual = anomalies.filter((a) => a.type === "unusual_amount");
    expect(unusual.length).toBeGreaterThanOrEqual(1);
    expect(unusual.some((a) => a.transaction.id === "outlier")).toBe(true);
  });

  test("detects potential duplicate charges", () => {
    const transactions: Transaction[] = [
      tx({ id: "a", date: "2025-01-15", amount: -29.99, merchant: "Netflix" }),
      tx({ id: "b", date: "2025-01-16", amount: -29.99, merchant: "Netflix" }),
    ];

    const anomalies = detectAnomalies(transactions);
    const duplicates = anomalies.filter((a) => a.type === "duplicate");
    expect(duplicates.length).toBeGreaterThanOrEqual(1);
    expect(duplicates[0]!.severity).toBe("medium");
  });

  test("does NOT flag duplicates outside the window", () => {
    const transactions: Transaction[] = [
      tx({ id: "a", date: "2025-01-01", amount: -29.99, merchant: "Netflix" }),
      tx({ id: "b", date: "2025-01-15", amount: -29.99, merchant: "Netflix" }),
    ];

    const anomalies = detectAnomalies(transactions, { duplicateWindowDays: 3 });
    const duplicates = anomalies.filter((a) => a.type === "duplicate");
    expect(duplicates).toHaveLength(0);
  });

  test("detects new merchants when historical baseline provided", () => {
    const historical: Transaction[] = [
      tx({ id: "h1", merchant: "Old Store", amount: -10 }),
      tx({ id: "h2", merchant: "Old Store", amount: -15 }),
    ];
    const current: Transaction[] = [
      tx({ id: "c1", merchant: "Brand New Place", amount: -25 }),
    ];

    const anomalies = detectAnomalies(current, {
      historicalTransactions: historical,
    });
    const newMerchants = anomalies.filter((a) => a.type === "new_merchant");
    expect(newMerchants.length).toBeGreaterThanOrEqual(1);
    expect(newMerchants[0]!.severity).toBe("low");
  });

  test("sorts anomalies by severity (high first)", () => {
    // Create a scenario with both duplicates (medium) and unusual amounts
    const baseline: Transaction[] = [];
    for (let i = 0; i < 10; i++) {
      baseline.push(
        tx({ id: `b-${i}`, date: "2025-01-01", amount: -10, merchant: "Regular" })
      );
    }
    const outlier = tx({
      id: "big",
      date: "2025-01-15",
      amount: -1000,
      merchant: "Regular",
    });

    const anomalies = detectAnomalies([...baseline, outlier]);
    if (anomalies.length > 1) {
      const severityOrder = { high: 0, medium: 1, low: 2 };
      for (let i = 1; i < anomalies.length; i++) {
        expect(
          severityOrder[anomalies[i - 1]!.severity]
        ).toBeLessThanOrEqual(severityOrder[anomalies[i]!.severity]);
      }
    }
  });

  test("merchant normalization is case-insensitive", () => {
    const transactions: Transaction[] = [
      tx({ id: "a", date: "2025-01-15", amount: -29.99, merchant: "NETFLIX" }),
      tx({ id: "b", date: "2025-01-16", amount: -29.99, merchant: "netflix" }),
    ];

    const anomalies = detectAnomalies(transactions);
    const duplicates = anomalies.filter((a) => a.type === "duplicate");
    expect(duplicates.length).toBeGreaterThanOrEqual(1);
  });
});
