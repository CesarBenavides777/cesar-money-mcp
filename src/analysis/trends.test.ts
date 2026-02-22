import { describe, expect, test } from "bun:test";
import { detectTrends } from "./trends.js";
import type { Transaction } from "./spending.js";

function tx(overrides: Partial<Transaction> = {}): Transaction {
  return {
    id: overrides.id ?? "tx-1",
    date: overrides.date ?? "2025-01-15",
    amount: overrides.amount ?? -50,
    merchant: overrides.merchant ?? "Store",
    category: overrides.category ?? { name: "Shopping" },
  };
}

describe("detectTrends", () => {
  test("returns empty array for empty transactions", () => {
    expect(detectTrends([])).toEqual([]);
  });

  test("returns empty array when fewer than minMonths of data", () => {
    const transactions: Transaction[] = [
      tx({ id: "1", date: "2025-01-15", amount: -100 }),
      tx({ id: "2", date: "2025-02-15", amount: -100 }),
    ];
    const result = detectTrends(transactions, { minMonths: 3 });
    expect(result).toHaveLength(0);
  });

  test("detects increasing spending trend", () => {
    const transactions: Transaction[] = [
      tx({ id: "1", date: "2025-01-15", amount: -100, category: { name: "Food" } }),
      tx({ id: "2", date: "2025-02-15", amount: -150, category: { name: "Food" } }),
      tx({ id: "3", date: "2025-03-15", amount: -200, category: { name: "Food" } }),
      tx({ id: "4", date: "2025-04-15", amount: -250, category: { name: "Food" } }),
    ];

    const result = detectTrends(transactions, { minMonths: 3 });
    expect(result).toHaveLength(1);
    expect(result[0]!.category).toBe("Food");
    expect(result[0]!.direction).toBe("increasing");
    expect(result[0]!.changePercent).toBeGreaterThan(0);
  });

  test("detects decreasing spending trend", () => {
    const transactions: Transaction[] = [
      tx({ id: "1", date: "2025-01-15", amount: -200, category: { name: "Entertainment" } }),
      tx({ id: "2", date: "2025-02-15", amount: -150, category: { name: "Entertainment" } }),
      tx({ id: "3", date: "2025-03-15", amount: -100, category: { name: "Entertainment" } }),
      tx({ id: "4", date: "2025-04-15", amount: -50, category: { name: "Entertainment" } }),
    ];

    const result = detectTrends(transactions, { minMonths: 3 });
    expect(result).toHaveLength(1);
    expect(result[0]!.direction).toBe("decreasing");
    expect(result[0]!.changePercent).toBeLessThan(0);
  });

  test("detects stable spending", () => {
    const transactions: Transaction[] = [
      tx({ id: "1", date: "2025-01-15", amount: -100, category: { name: "Utilities" } }),
      tx({ id: "2", date: "2025-02-15", amount: -101, category: { name: "Utilities" } }),
      tx({ id: "3", date: "2025-03-15", amount: -99, category: { name: "Utilities" } }),
      tx({ id: "4", date: "2025-04-15", amount: -100, category: { name: "Utilities" } }),
    ];

    const result = detectTrends(transactions, { minMonths: 3, stableThreshold: 5 });
    expect(result).toHaveLength(1);
    expect(result[0]!.direction).toBe("stable");
  });

  test("only considers expenses (negative amounts)", () => {
    const transactions: Transaction[] = [
      tx({ id: "1", date: "2025-01-15", amount: 3000, category: { name: "Income" } }),
      tx({ id: "2", date: "2025-02-15", amount: 3000, category: { name: "Income" } }),
      tx({ id: "3", date: "2025-03-15", amount: 3000, category: { name: "Income" } }),
    ];

    const result = detectTrends(transactions);
    expect(result).toHaveLength(0);
  });

  test("filters by category when provided", () => {
    const transactions: Transaction[] = [
      tx({ id: "1", date: "2025-01-15", amount: -100, category: { name: "Food" } }),
      tx({ id: "2", date: "2025-02-15", amount: -200, category: { name: "Food" } }),
      tx({ id: "3", date: "2025-03-15", amount: -300, category: { name: "Food" } }),
      tx({ id: "4", date: "2025-01-15", amount: -50, category: { name: "Transport" } }),
      tx({ id: "5", date: "2025-02-15", amount: -50, category: { name: "Transport" } }),
      tx({ id: "6", date: "2025-03-15", amount: -50, category: { name: "Transport" } }),
    ];

    const result = detectTrends(transactions, {
      minMonths: 3,
      categories: ["Food"],
    });
    expect(result).toHaveLength(1);
    expect(result[0]!.category).toBe("Food");
  });

  test("handles null categories", () => {
    const transactions: Transaction[] = [
      { id: "1", date: "2025-01-15", amount: -100, merchant: "Store", category: null },
      { id: "2", date: "2025-02-15", amount: -100, merchant: "Store", category: null },
      { id: "3", date: "2025-03-15", amount: -100, merchant: "Store", category: null },
    ];

    const result = detectTrends(transactions, { minMonths: 3 });
    expect(result).toHaveLength(1);
    expect(result[0]!.category).toBe("Uncategorized");
  });

  test("sorts trends by absolute change descending", () => {
    const transactions: Transaction[] = [
      // Small change
      tx({ id: "1", date: "2025-01-15", amount: -100, category: { name: "A" } }),
      tx({ id: "2", date: "2025-02-15", amount: -110, category: { name: "A" } }),
      tx({ id: "3", date: "2025-03-15", amount: -120, category: { name: "A" } }),
      // Big change
      tx({ id: "4", date: "2025-01-15", amount: -100, category: { name: "B" } }),
      tx({ id: "5", date: "2025-02-15", amount: -300, category: { name: "B" } }),
      tx({ id: "6", date: "2025-03-15", amount: -500, category: { name: "B" } }),
    ];

    const result = detectTrends(transactions, { minMonths: 3 });
    expect(result.length).toBe(2);
    expect(Math.abs(result[0]!.changePercent)).toBeGreaterThanOrEqual(
      Math.abs(result[1]!.changePercent)
    );
  });

  test("includes correct data points per category", () => {
    const transactions: Transaction[] = [
      tx({ id: "1", date: "2025-01-10", amount: -50, category: { name: "Food" } }),
      tx({ id: "2", date: "2025-01-20", amount: -50, category: { name: "Food" } }),
      tx({ id: "3", date: "2025-02-15", amount: -75, category: { name: "Food" } }),
      tx({ id: "4", date: "2025-03-15", amount: -100, category: { name: "Food" } }),
    ];

    const result = detectTrends(transactions, { minMonths: 3 });
    expect(result).toHaveLength(1);
    expect(result[0]!.dataPoints).toHaveLength(3); // 3 months
    expect(result[0]!.dataPoints[0]!.period).toBe("2025-01");
    expect(result[0]!.dataPoints[0]!.amount).toBe(100); // Two $50 txns in Jan
  });
});
