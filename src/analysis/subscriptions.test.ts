import { describe, expect, test } from "bun:test";
import {
  analyzeSubscriptions,
  type RecurringTransaction,
} from "./subscriptions.js";

function sub(overrides: Partial<RecurringTransaction> = {}): RecurringTransaction {
  return {
    id: overrides.id ?? "sub-1",
    date: overrides.date ?? "2025-01-15",
    amount: overrides.amount ?? -14.99,
    merchant: overrides.merchant ?? "Netflix",
  };
}

describe("analyzeSubscriptions", () => {
  test("returns empty summary for no transactions", () => {
    const result = analyzeSubscriptions([]);
    expect(result.totalMonthly).toBe(0);
    expect(result.totalAnnual).toBe(0);
    expect(result.subscriptions).toHaveLength(0);
    expect(result.recentChanges).toHaveLength(0);
  });

  test("groups by merchant (case-insensitive)", () => {
    const transactions: RecurringTransaction[] = [
      sub({ id: "1", date: "2025-01-15", merchant: "Netflix", amount: -14.99 }),
      sub({ id: "2", date: "2025-02-15", merchant: "NETFLIX", amount: -14.99 }),
    ];

    const result = analyzeSubscriptions(transactions);
    expect(result.subscriptions).toHaveLength(1);
    expect(result.subscriptions[0]!.amount).toBe(14.99);
  });

  test("calculates annual cost for monthly subscription", () => {
    const transactions: RecurringTransaction[] = [
      sub({ id: "1", date: "2025-01-15", amount: -9.99 }),
      sub({ id: "2", date: "2025-02-15", amount: -9.99 }),
    ];

    const result = analyzeSubscriptions(transactions);
    expect(result.subscriptions).toHaveLength(1);
    expect(result.subscriptions[0]!.annualCost).toBeCloseTo(9.99 * 12, 0);
    expect(result.subscriptions[0]!.frequency).toBe("monthly");
  });

  test("detects price changes", () => {
    const transactions: RecurringTransaction[] = [
      sub({ id: "1", date: "2025-01-15", amount: -9.99, merchant: "Spotify" }),
      sub({ id: "2", date: "2025-02-15", amount: -10.99, merchant: "Spotify" }),
    ];

    const result = analyzeSubscriptions(transactions);
    expect(result.subscriptions[0]!.priceChanged).toBe(true);
    expect(result.recentChanges).toHaveLength(1);
  });

  test("no price change for consistent amounts", () => {
    const transactions: RecurringTransaction[] = [
      sub({ id: "1", date: "2025-01-15", amount: -9.99, merchant: "Hulu" }),
      sub({ id: "2", date: "2025-02-15", amount: -9.99, merchant: "Hulu" }),
      sub({ id: "3", date: "2025-03-15", amount: -9.99, merchant: "Hulu" }),
    ];

    const result = analyzeSubscriptions(transactions);
    expect(result.subscriptions[0]!.priceChanged).toBe(false);
    expect(result.recentChanges).toHaveLength(0);
  });

  test("computes total monthly and annual costs", () => {
    const transactions: RecurringTransaction[] = [
      sub({ id: "1", date: "2025-01-15", amount: -10, merchant: "Service A" }),
      sub({ id: "2", date: "2025-02-15", amount: -10, merchant: "Service A" }),
      sub({ id: "3", date: "2025-01-20", amount: -20, merchant: "Service B" }),
      sub({ id: "4", date: "2025-02-20", amount: -20, merchant: "Service B" }),
    ];

    const result = analyzeSubscriptions(transactions);
    expect(result.subscriptions).toHaveLength(2);
    // Monthly: $10 + $20 = $30, Annual: $360
    expect(result.totalMonthly).toBe(30);
    expect(result.totalAnnual).toBe(360);
  });

  test("sorts subscriptions by annual cost descending", () => {
    const transactions: RecurringTransaction[] = [
      sub({ id: "1", date: "2025-01-15", amount: -5, merchant: "Cheap" }),
      sub({ id: "2", date: "2025-02-15", amount: -5, merchant: "Cheap" }),
      sub({ id: "3", date: "2025-01-15", amount: -50, merchant: "Expensive" }),
      sub({ id: "4", date: "2025-02-15", amount: -50, merchant: "Expensive" }),
    ];

    const result = analyzeSubscriptions(transactions);
    expect(result.subscriptions[0]!.merchant).toBe("Expensive");
    expect(result.subscriptions[1]!.merchant).toBe("Cheap");
  });

  test("builds price history", () => {
    const transactions: RecurringTransaction[] = [
      sub({ id: "1", date: "2025-01-15", amount: -9.99, merchant: "Netflix" }),
      sub({ id: "2", date: "2025-02-15", amount: -14.99, merchant: "Netflix" }),
      sub({ id: "3", date: "2025-03-15", amount: -14.99, merchant: "Netflix" }),
    ];

    const result = analyzeSubscriptions(transactions);
    const netflix = result.subscriptions[0]!;
    expect(netflix.priceHistory).toHaveLength(3);
    expect(netflix.priceHistory[0]!.amount).toBe(9.99);
    expect(netflix.priceHistory[1]!.amount).toBe(14.99);
  });

  test("single transaction defaults to monthly frequency", () => {
    const result = analyzeSubscriptions([
      sub({ id: "1", date: "2025-01-15", amount: -9.99 }),
    ]);
    expect(result.subscriptions[0]!.frequency).toBe("monthly");
  });
});
