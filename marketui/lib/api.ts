import { DATA_BASE_URL } from "../app/config";
import type { HealthResponse, IndexResponse, NarrativeRecord, TradeRecord } from "./types";

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${DATA_BASE_URL}${path}`);
  if (!res.ok) {
    throw new Error(`GET ${path} failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

async function fetchNdjson<T>(path: string): Promise<T[]> {
  const res = await fetch(`${DATA_BASE_URL}${path}`);
  if (!res.ok) {
    throw new Error(`GET ${path} failed: ${res.status}`);
  }
  const text = await res.text();
  return text
    .trim()
    .split("\n")
    .filter((line) => line.length > 0)
    .map((line) => JSON.parse(line) as T);
}

/** GET /health */
export async function fetchHealth(): Promise<HealthResponse> {
  return fetchJson<HealthResponse>("/health");
}

/** GET /blobs — list available narrative blob dates */
export async function fetchIndex(): Promise<IndexResponse> {
  return fetchJson<IndexResponse>("/blobs");
}

/** GET /blobs/:date — fetch narrative records for a date */
export async function fetchBlob(date: string): Promise<NarrativeRecord[]> {
  return fetchNdjson<NarrativeRecord>(`/blobs/${date}`);
}

/** GET /trades — list available trade blob dates */
export async function fetchTradeIndex(): Promise<IndexResponse> {
  return fetchJson<IndexResponse>("/trades");
}

/** GET /trades/:date — fetch trade records for a date */
export async function fetchTradeBlob(date: string): Promise<TradeRecord[]> {
  return fetchNdjson<TradeRecord>(`/trades/${date}`);
}

/** Extract date string (YYYY-MM-DD) from a blob filename like decisions_2026-07-28.jsonl */
export function dateFromFilename(filename: string): string {
  const match = filename.match(/decisions_(\d{4}-\d{2}-\d{2})\.jsonl/);
  return match ? match[1] : filename;
}
