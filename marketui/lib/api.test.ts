import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  fetchHealth,
  fetchIndex,
  fetchBlob,
  fetchTradeIndex,
  fetchTradeBlob,
  dateFromFilename,
} from "./api";

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("dateFromFilename", () => {
  it("extracts date from standard filename", () => {
    expect(dateFromFilename("decisions_2026-08-01.jsonl")).toBe("2026-08-01");
  });

  it("returns raw string when pattern does not match", () => {
    expect(dateFromFilename("random.txt")).toBe("random.txt");
  });

  it("handles multiple dates in path — picks the one in the pattern", () => {
    expect(dateFromFilename("decisions_2025-12-31.jsonl")).toBe("2025-12-31");
  });
});

describe("fetchHealth", () => {
  it("returns parsed JSON on success", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ status: "ok" }),
    } as Response);

    const result = await fetchHealth();
    expect(result).toEqual({ status: "ok" });
  });

  it("throws on non-ok response", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: false,
      status: 500,
    } as Response);

    await expect(fetchHealth()).rejects.toThrow("failed: 500");
  });
});

describe("fetchIndex", () => {
  it("returns index response", async () => {
    const body = { blobs: [{ filename: "decisions_2026-08-01.jsonl" }] };
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(body),
    } as Response);

    const result = await fetchIndex();
    expect(result.blobs).toHaveLength(1);
    expect(result.blobs[0].filename).toBe("decisions_2026-08-01.jsonl");
  });
});

describe("fetchTradeIndex", () => {
  it("returns trade index response", async () => {
    const body = { blobs: [{ filename: "decisions_2026-07-30.jsonl" }] };
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(body),
    } as Response);

    const result = await fetchTradeIndex();
    expect(result.blobs).toHaveLength(1);
  });
});

describe("fetchBlob (NDJSON)", () => {
  it("parses newline-delimited JSON", async () => {
    const ndjson = '{"content":"hello","written_at":"2026-08-01T00:00:00Z"}\n{"content":"world","written_at":"2026-08-01T01:00:00Z"}\n';
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      text: () => Promise.resolve(ndjson),
    } as Response);

    const result = await fetchBlob("2026-08-01");
    expect(result).toHaveLength(2);
    expect(result[0].content).toBe("hello");
    expect(result[1].content).toBe("world");
  });

  it("handles empty response", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      text: () => Promise.resolve(""),
    } as Response);

    const result = await fetchBlob("2026-08-01");
    expect(result).toHaveLength(0);
  });

  it("throws on non-ok response", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: false,
      status: 404,
    } as Response);

    await expect(fetchBlob("2026-08-01")).rejects.toThrow("failed: 404");
  });
});

describe("fetchTradeBlob (NDJSON)", () => {
  it("parses trade records", async () => {
    const record = {
      symbol: "BTCUSDT",
      signal_type: "aggressive_buyer",
      cluster_id: 0,
      anomaly_score: 0.85,
      action: "BUY",
      entry_price: 50000,
      raw_quantity: 1.0,
      timestamp_utc: "2026-08-01T12:00:00Z",
      risk_approved: true,
      sized_quantity: 0.42,
    };
    const ndjson = JSON.stringify(record) + "\n";
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      text: () => Promise.resolve(ndjson),
    } as Response);

    const result = await fetchTradeBlob("2026-08-01");
    expect(result).toHaveLength(1);
    expect(result[0].symbol).toBe("BTCUSDT");
    expect(result[0].sized_quantity).toBe(0.42);
  });
});
