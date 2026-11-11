import { test, expect } from "@playwright/test";

const MOCK_PORTFOLIO = {
  cash: 85.5,
  starting_balance: 100.0,
  positions: {
    BTCUSDT: {
      quantity: 0.0002,
      avg_entry_price: 72500.0,
      opened_at: "2026-11-10T12:00:00+00:00",
    },
    ETHUSDT: {
      quantity: 0.05,
      avg_entry_price: 3800.0,
      opened_at: "2026-11-10T13:00:00+00:00",
    },
  },
  realized_pnl: 1.25,
  updated_at: "2026-11-10T14:30:00+00:00",
};

const API_GLOB = "**/localhost:5001/portfolio";

function mockPortfolioRoute(page: import("@playwright/test").Page) {
  return page.route(API_GLOB, (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(MOCK_PORTFOLIO),
    }),
  );
}

test.describe("Portfolio page", () => {
  test("renders page heading and disclaimer", async ({ page }) => {
    await mockPortfolioRoute(page);
    await page.goto("/portfolio");

    await expect(page.getByRole("heading", { name: "Paper Portfolio" })).toBeVisible();
    await expect(page.getByText("Paper Trading:")).toBeVisible();
  });

  test("displays summary cards with correct values", async ({ page }) => {
    await mockPortfolioRoute(page);
    await page.goto("/portfolio");

    const cards = page.getByTestId("summary-cards");
    await expect(cards).toBeVisible();

    await expect(cards.getByText("Cash")).toBeVisible();
    await expect(cards.getByText("Positions")).toBeVisible();
    await expect(cards.getByText("Realized P&L")).toBeVisible();
    await expect(cards.getByText("Return")).toBeVisible();

    // 2 positions
    await expect(cards.getByText("2", { exact: true }).first()).toBeVisible();
  });

  test("displays positions table with symbols", async ({ page }) => {
    await mockPortfolioRoute(page);
    await page.goto("/portfolio");

    const table = page.getByTestId("positions-table");
    await expect(table).toBeVisible();

    // Column headers
    await expect(table.getByText("Symbol")).toBeVisible();
    await expect(table.getByText("Quantity")).toBeVisible();
    await expect(table.getByText("Avg Entry")).toBeVisible();
    await expect(table.getByText("Cost Basis")).toBeVisible();

    // Position rows
    await expect(table.getByText("BTCUSDT")).toBeVisible();
    await expect(table.getByText("ETHUSDT")).toBeVisible();
  });

  test("shows last updated timestamp", async ({ page }) => {
    await mockPortfolioRoute(page);
    await page.goto("/portfolio");

    const updated = page.getByTestId("updated-at");
    await expect(updated).toBeVisible();
    await expect(updated).toContainText("Last updated:");
  });

  test("shows error state when server is unreachable", async ({ page }) => {
    await page.route(API_GLOB, (route) =>
      route.fulfill({ status: 500, body: "Internal Server Error" }),
    );
    await page.goto("/portfolio");

    await expect(page.getByTestId("error-state")).toBeVisible();
    await expect(page.getByText("Could not load portfolio")).toBeVisible();
  });

  test("shows no positions message when portfolio is empty", async ({ page }) => {
    await page.route(API_GLOB, (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          ...MOCK_PORTFOLIO,
          positions: {},
        }),
      }),
    );
    await page.goto("/portfolio");

    await expect(page.getByTestId("no-positions")).toBeVisible();
    await expect(page.getByText("No open positions")).toBeVisible();
  });
});

test.describe("Navigation", () => {
  test("portfolio link is present in nav", async ({ page }) => {
    await mockPortfolioRoute(page);
    await page.goto("/");

    const portfolioLink = page.getByRole("link", { name: "Portfolio" });
    await expect(portfolioLink).toBeVisible();
  });

  test("portfolio link navigates to /portfolio", async ({ page }) => {
    await mockPortfolioRoute(page);
    await page.goto("/");

    await page.getByRole("link", { name: "Portfolio" }).click();
    await expect(page).toHaveURL(/\/portfolio/);
    await expect(page.getByRole("heading", { name: "Paper Portfolio" })).toBeVisible();
  });
});
