import { defineConfig } from "@playwright/test";

const baseURL = process.env.PLAYWRIGHT_BASE_URL || "http://localhost:3000";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  retries: 0,
  use: {
    baseURL,
    headless: true,
  },
  // Only start a dev server when no PLAYWRIGHT_BASE_URL is set (local dev).
  // In make test-e2e the docker-compose stack serves marketui on port 3001.
  ...(!process.env.PLAYWRIGHT_BASE_URL && {
    webServer: {
      command: "npm run dev -- --port 3000",
      port: 3000,
      reuseExistingServer: true,
      timeout: 30_000,
    },
  }),
});
