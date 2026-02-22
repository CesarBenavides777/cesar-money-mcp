import { describe, expect, test } from "bun:test";
import {
  forecastCashflow,
  type Account,
  type RecurringItem,
} from "./forecasting.js";
import type { Transaction } from "./spending.js";

function makeAccount(overrides: Partial<Account> = {}): Account {
  return {
    id: overrides.id ?? "acc-1",
    displayName: overrides.displayName ?? "Checking",
    currentBalance: overrides.currentBalance ?? 5000,
    isAsset: overrides.isAsset ?? false,
  };
}

function makeTx(overrides: Partial<Transaction> = {}): Transaction {
  return {
    id: overrides.id ?? "tx-1",
    date: overrides.date ?? "2025-01-15",
    amount: overrides.amount ?? -50,
    merchant: overrides.merchant ?? "Grocery Store",
    category: overrides.category ?? { name: "Food" },
  };
}

function makeRecurring(overrides: Partial<RecurringItem> = {}): RecurringItem {
  return {
    id: overrides.id ?? "rec-1",
    merchant: overrides.merchant ?? "Salary",
    amount: overrides.amount ?? 3000,
    frequency: overrides.frequency ?? "monthly",
    nextDate: overrides.nextDate ?? "2025-02-01",
  };
}

describe("forecastCashflow", () => {
  test("returns correct current balance from accounts", () => {
    const accounts = [
      makeAccount({ id: "a1", currentBalance: 5000 }),
      makeAccount({ id: "a2", currentBalance: 3000 }),
    ];

    const result = forecastCashflow(accounts, [], []);
    expect(result.currentBalance).toBe(8000);
  });

  test("excludes asset-only accounts from balance", () => {
    const accounts = [
      makeAccount({ id: "a1", currentBalance: 5000, isAsset: false }),
      makeAccount({ id: "a2", currentBalance: 100000, isAsset: true }),
    ];

    const result = forecastCashflow(accounts, [], []);
    expect(result.currentBalance).toBe(5000);
  });

  test("generates correct number of daily projections", () => {
    const result = forecastCashflow(
      [makeAccount()],
      [],
      [],
      { forecastDays: 30 }
    );
    expect(result.forecastDays).toBe(30);
    expect(result.dailyProjections).toHaveLength(30);
  });

  test("calculates recurring income and expenses", () => {
    const recurring = [
      makeRecurring({ id: "r1", amount: 3000, frequency: "monthly" }),
      makeRecurring({ id: "r2", amount: -1500, frequency: "monthly" }),
      makeRecurring({ id: "r3", amount: -100, frequency: "weekly" }),
    ];

    const result = forecastCashflow([makeAccount()], [], recurring);
    expect(result.recurringIncome).toBeGreaterThan(0);
    expect(result.recurringExpenses).toBeGreaterThan(0);
  });

  test("projected balance reflects recurring flows", () => {
    const accounts = [makeAccount({ currentBalance: 10000 })];
    const recurring = [
      makeRecurring({ amount: 5000, frequency: "monthly" }),
    ];

    const result = forecastCashflow(accounts, [], recurring, {
      forecastDays: 30,
    });
    // With income and no expenses (and no discretionary), balance should increase
    expect(result.projectedBalance).toBeGreaterThan(10000);
  });

  test("confidence bounds widen over time", () => {
    const result = forecastCashflow(
      [makeAccount()],
      [
        makeTx({ id: "1", date: "2025-01-01", amount: -30 }),
        makeTx({ id: "2", date: "2025-01-02", amount: -50 }),
        makeTx({ id: "3", date: "2025-01-03", amount: -100 }),
      ],
      [],
      { forecastDays: 30 }
    );

    if (result.dailyProjections.length >= 2) {
      const early = result.dailyProjections[0]!;
      const late = result.dailyProjections[result.dailyProjections.length - 1]!;
      const earlyRange = early.upper - early.lower;
      const lateRange = late.upper - late.lower;
      expect(lateRange).toBeGreaterThanOrEqual(earlyRange);
    }
  });

  test("respects accountIds filter", () => {
    const accounts = [
      makeAccount({ id: "keep", currentBalance: 1000 }),
      makeAccount({ id: "exclude", currentBalance: 9000 }),
    ];

    const result = forecastCashflow(accounts, [], [], {
      accountIds: ["keep"],
    });
    expect(result.currentBalance).toBe(1000);
  });

  test("daily projections have valid date format", () => {
    const result = forecastCashflow([makeAccount()], [], [], {
      forecastDays: 5,
    });
    for (const point of result.dailyProjections) {
      expect(point.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    }
  });
});
