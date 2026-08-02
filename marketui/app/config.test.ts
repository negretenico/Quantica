import { describe, it, expect, vi, beforeEach } from "vitest";

describe("DATA_BASE_URL", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it("defaults to empty string when env var is not set", async () => {
    vi.stubEnv("NEXT_PUBLIC_DATA_BASE_URL", "");
    const { DATA_BASE_URL } = await import("./config");
    expect(DATA_BASE_URL).toBe("");
  });

  it("strips trailing slashes", async () => {
    vi.stubEnv("NEXT_PUBLIC_DATA_BASE_URL", "http://localhost:5001///");
    const { DATA_BASE_URL } = await import("./config");
    expect(DATA_BASE_URL).toBe("http://localhost:5001");
  });

  it("preserves URL without trailing slash", async () => {
    vi.stubEnv("NEXT_PUBLIC_DATA_BASE_URL", "http://localhost:5001");
    const { DATA_BASE_URL } = await import("./config");
    expect(DATA_BASE_URL).toBe("http://localhost:5001");
  });
});
