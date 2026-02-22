import { describe, expect, test } from "bun:test";
import { analyzeSpending, type Transaction } from "./spending.js";

function tx(
  overrides: Partial<Transaction> & { id?: string } = {}
): Transaction {
  return {
    id: overrides.id ?? "tx-1",
    date: overrides.date ?? "2025-01-15",
    amount: overrides.amount ?? -50,
    merchant: overrides.merchant ?? "Test Store",
    category: overrides.category ?? { name: "Shopping" },
  };
}

describe("analyzeSpending", () => {
  test("returns zeroed result for empty transactions", () => {
    const result = analyzeSpending([]);
    expect(result.totalSpending).toBe(0);
    expect(result.totalIncome).toBe(0);
    expect(result.netCashflow).toBe(0);
    expect(result.topCategories).toHaveLength(0);
  });

  test("separates expenses and income", () => {
    const transactions: Transaction[] = [
      tx({ id: "1", amount: -100, category: { name: "Food" } }),
      tx({ id: "2", amount: -50, category: { name: "Transport" } }),
      tx({ id: "3", amount: 3000, merchant: "Employer", category: { name: "Income" } }),
    ];

    const result = analyzeSpending(transactions);
    expect(result.totalSpending).toBe(150);
    expect(result.totalIncome).toBe(3000);
    expect(result.netCashflow).toBe(2850);
  });

  test("groups spending by category", () => {
    const transactions: Transaction[] = [
      tx({ id: "1", amount: -100, category: { name: "Food" } }),
      tx({ id: "2", amount: -75, category: { name: "Food" } }),
      tx({ id: "3", amount: -50, category: { name: "Transport" } }),
    ];

    const result = analyzeSpending(transactions);
    expect(result.topCategories).toHaveLength(2);
    expect(result.topCategories[0]!.category).toBe("Food");
    expect(result.topCategories[0]!.amount).toBe(175);
    expect(result.topCategories[0]!.transactionCount).toBe(2);
    expect(result.topCategories[1]!.category).toBe("Transport");
    expect(result.topCategories[1]!.amount).toBe(50);
  });

  test("respects topN option", () => {
    const transactions: Transaction[] = [
      tx({ id: "1", amount: -100, category: { name: "A" } }),
      tx({ id: "2", amount: -75, category: { name: "B" } }),
      tx({ id: "3", amount: -50, category: { name: "C" } }),
    ];

    const result = analyzeSpending(transactions, { topN: 2 });
    expect(result.topCategories).toHaveLength(2);
    expect(result.topCategories[0]!.category).toBe("A");
    expect(result.topCategories[1]!.category).toBe("B");
  });

  test("filters by date range", () => {
    const transactions: Transaction[] = [
      tx({ id: "1", date: "2025-01-01", amount: -100 }),
      tx({ id: "2", date: "2025-01-15", amount: -50 }),
      tx({ id: "3", date: "2025-02-01", amount: -200 }),
    ];

    const result = analyzeSpending(transactions, {
      startDate: "2025-01-01",
      endDate: "2025-01-31",
    });
    expect(result.totalSpending).toBe(150);
  });

  test("handles null/missing categories gracefully", () => {
    const transactions: Transaction[] = [
      { id: "1", date: "2025-01-15", amount: -100, merchant: "Store A", category: null },
      { id: "2", date: "2025-01-15", amount: -50, merchant: "Store B", category: undefined },
      { id: "3", date: "2025-01-15", amount: -75, merchant: "Store C", category: { name: "Food" } },
    ];

    const result = analyzeSpending(transactions);
    expect(result.totalSpending).toBe(225);
    const uncategorized = result.topCategories.find(
      (c) => c.category === "Uncategorized"
    );
    expect(uncategorized).toBeDefined();
    expect(uncategorized!.amount).toBe(150);
  });

  test("computes daily average correctly", () => {
    const transactions: Transaction[] = [
      tx({ id: "1", date: "2025-01-01", amount: -100 }),
      tx({ id: "2", date: "2025-01-10", amount: -100 }),
    ];

    const result = analyzeSpending(transactions, {
      startDate: "2025-01-01",
      endDate: "2025-01-10",
    });
    // 10 days inclusive, $200 total = $20/day
    expect(result.dailyAverage).toBe(20);
  });

  test("compares to prior period", () => {
    const current: Transaction[] = [
      tx({ id: "1", amount: -300 }),
    ];
    const prior: Transaction[] = [
      tx({ id: "2", amount: -200 }),
    ];

    const result = analyzeSpending(current, {
      priorPeriodTransactions: prior,
    });

    expect(result.comparisonToPriorPeriod).toBeDefined();
    expect(result.comparisonToPriorPeriod!.spendingChange).toBe(100);
    expect(result.comparisonToPriorPeriod!.spendingChangePercent).toBe(50);
  });

  test("percentages sum to ~100 for categories", () => {
    const transactions: Transaction[] = [
      tx({ id: "1", amount: -60, category: { name: "A" } }),
      tx({ id: "2", amount: -30, category: { name: "B" } }),
      tx({ id: "3", amount: -10, category: { name: "C" } }),
    ];

    const result = analyzeSpending(transactions);
    const totalPct = result.topCategories.reduce(
      (sum, c) => sum + c.percentage,
      0
    );
    expect(totalPct).toBeCloseTo(100, 0);
  });
});
