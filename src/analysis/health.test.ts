import { describe, expect, test } from "bun:test";
import {
  calculateHealthScore,
  type HealthAccount,
  type BudgetItem,
  type NetWorthPoint,
} from "./health.js";
import type { Transaction } from "./spending.js";

function makeTx(overrides: Partial<Transaction> = {}): Transaction {
  return {
    id: overrides.id ?? "tx-1",
    date: overrides.date ?? "2025-01-15",
    amount: overrides.amount ?? -50,
    merchant: overrides.merchant ?? "Store",
    category: overrides.category ?? { name: "Shopping" },
  };
}

function makeAccount(overrides: Partial<HealthAccount> = {}): HealthAccount {
  return {
    id: overrides.id ?? "acc-1",
    displayName: overrides.displayName ?? "Checking",
    currentBalance: overrides.currentBalance ?? 5000,
    type: overrides.type ?? "depository",
  };
}

describe("calculateHealthScore", () => {
  test("returns score between 0 and 100", () => {
    const result = calculateHealthScore({
      accounts: [makeAccount()],
      transactions: [
        makeTx({ id: "1", amount: 5000 }),
        makeTx({ id: "2", amount: -3000 }),
      ],
      budgets: [],
      netWorthHistory: [],
    });

    expect(result.overall).toBeGreaterThanOrEqual(0);
    expect(result.overall).toBeLessThanOrEqual(100);
  });

  test("returns neutral scores for empty data", () => {
    const result = calculateHealthScore({
      accounts: [],
      transactions: [],
      budgets: [],
      netWorthHistory: [],
    });

    // With no data, components default to 50
    expect(result.overall).toBe(50);
  });

  test("high savings rate yields high savings score", () => {
    const transactions: Transaction[] = [
      makeTx({ id: "1", amount: 10000 }),  // income
      makeTx({ id: "2", amount: -2000 }),  // spending
    ];

    const result = calculateHealthScore({
      accounts: [makeAccount()],
      transactions,
      budgets: [],
      netWorthHistory: [],
    });

    // 80% savings rate should score very high
    expect(result.components.savingsRate.score).toBeGreaterThan(80);
    expect(result.components.savingsRate.value).toBe(80);
  });

  test("negative savings rate scores low", () => {
    const transactions: Transaction[] = [
      makeTx({ id: "1", amount: 2000 }),   // income
      makeTx({ id: "2", amount: -5000 }),  // spending > income
    ];

    const result = calculateHealthScore({
      accounts: [makeAccount()],
      transactions,
      budgets: [],
      netWorthHistory: [],
    });

    expect(result.components.savingsRate.score).toBeLessThan(30);
    expect(result.components.savingsRate.value).toBeLessThan(0);
  });

  test("low debt ratio scores high", () => {
    const accounts: HealthAccount[] = [
      makeAccount({ id: "a1", type: "depository", currentBalance: 50000 }),
      makeAccount({ id: "a2", type: "investment", currentBalance: 100000 }),
      makeAccount({ id: "a3", type: "credit", currentBalance: 2000 }),
    ];

    const result = calculateHealthScore({
      accounts,
      transactions: [],
      budgets: [],
      netWorthHistory: [],
    });

    // Debt ratio = 2000/150000 ≈ 1.3% → should score high
    expect(result.components.debtRatio.score).toBeGreaterThan(90);
  });

  test("high debt ratio scores low", () => {
    const accounts: HealthAccount[] = [
      makeAccount({ id: "a1", type: "depository", currentBalance: 5000 }),
      makeAccount({ id: "a2", type: "credit", currentBalance: 10000 }),
      makeAccount({ id: "a3", type: "loan", currentBalance: 50000 }),
    ];

    const result = calculateHealthScore({
      accounts,
      transactions: [],
      budgets: [],
      netWorthHistory: [],
    });

    // Debt ratio = 60000/5000 = 1200% → score 0
    expect(result.components.debtRatio.score).toBe(0);
  });

  test("perfect budget adherence scores 100", () => {
    const budgets: BudgetItem[] = [
      { category: "Food", budgeted: 500, actual: 400 },
      { category: "Transport", budgeted: 200, actual: 150 },
      { category: "Entertainment", budgeted: 100, actual: 100 },
    ];

    const result = calculateHealthScore({
      accounts: [],
      transactions: [],
      budgets,
      netWorthHistory: [],
    });

    expect(result.components.budgetAdherence.score).toBe(100);
    expect(result.components.budgetAdherence.value).toBe(100);
  });

  test("poor budget adherence scores low", () => {
    const budgets: BudgetItem[] = [
      { category: "Food", budgeted: 500, actual: 800 },
      { category: "Transport", budgeted: 200, actual: 400 },
      { category: "Entertainment", budgeted: 100, actual: 50 },
    ];

    const result = calculateHealthScore({
      accounts: [],
      transactions: [],
      budgets,
      netWorthHistory: [],
    });

    // 1 out of 3 on budget = 33%
    expect(result.components.budgetAdherence.score).toBeCloseTo(33.33, 0);
  });

  test("positive net worth trend scores well", () => {
    const netWorthHistory: NetWorthPoint[] = [
      { date: "2025-01-01", netWorth: 100000 },
      { date: "2025-02-01", netWorth: 105000 },
      { date: "2025-03-01", netWorth: 110000 },
      { date: "2025-04-01", netWorth: 115000 },
    ];

    const result = calculateHealthScore({
      accounts: [],
      transactions: [],
      budgets: [],
      netWorthHistory,
    });

    expect(result.components.netWorthTrend.score).toBeGreaterThan(60);
    expect(result.components.netWorthTrend.value).toBeGreaterThan(0);
  });

  test("declining net worth trend scores poorly", () => {
    const netWorthHistory: NetWorthPoint[] = [
      { date: "2025-01-01", netWorth: 100000 },
      { date: "2025-02-01", netWorth: 90000 },
      { date: "2025-03-01", netWorth: 80000 },
    ];

    const result = calculateHealthScore({
      accounts: [],
      transactions: [],
      budgets: [],
      netWorthHistory,
    });

    expect(result.components.netWorthTrend.score).toBeLessThan(50);
    expect(result.components.netWorthTrend.value).toBeLessThan(0);
  });

  test("generates recommendations for weak areas", () => {
    const result = calculateHealthScore({
      accounts: [
        makeAccount({ id: "a1", type: "depository", currentBalance: 500 }),
        makeAccount({ id: "a2", type: "credit", currentBalance: 10000 }),
      ],
      transactions: [
        makeTx({ id: "1", amount: 3000 }),
        makeTx({ id: "2", amount: -4000 }),
      ],
      budgets: [
        { category: "Food", budgeted: 500, actual: 800 },
      ],
      netWorthHistory: [
        { date: "2025-01-01", netWorth: 10000 },
        { date: "2025-02-01", netWorth: 5000 },
      ],
    });

    expect(result.recommendations.length).toBeGreaterThan(0);
    // Should have recommendations for savings, debt, emergency fund, budget, net worth
    expect(result.recommendations.length).toBeGreaterThanOrEqual(3);
  });

  test("all component scores are between 0 and 100", () => {
    const result = calculateHealthScore({
      accounts: [
        makeAccount({ id: "a1", type: "depository", currentBalance: 100 }),
        makeAccount({ id: "a2", type: "loan", currentBalance: 999999 }),
      ],
      transactions: [
        makeTx({ id: "1", amount: 1000 }),
        makeTx({ id: "2", amount: -5000 }),
      ],
      budgets: [
        { category: "All", budgeted: 100, actual: 9999 },
      ],
      netWorthHistory: [
        { date: "2025-01-01", netWorth: 100000 },
        { date: "2025-06-01", netWorth: -50000 },
      ],
    });

    for (const [, component] of Object.entries(result.components)) {
      expect(component.score).toBeGreaterThanOrEqual(0);
      expect(component.score).toBeLessThanOrEqual(100);
    }
    expect(result.overall).toBeGreaterThanOrEqual(0);
    expect(result.overall).toBeLessThanOrEqual(100);
  });
});
