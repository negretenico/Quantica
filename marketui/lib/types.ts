export interface HealthResponse {
  status: string;
}

export interface BlobEntry {
  filename: string;
}

export interface IndexResponse {
  blobs: BlobEntry[];
}

/** Single JSONL record inside a narrative blob file (decisions_YYYY-MM-DD.jsonl) */
export interface NarrativeRecord {
  content: string;
  written_at: string;
}

/** Single JSONL record inside a trade blob file (decisions_YYYY-MM-DD.jsonl) */
export interface TradeRecord {
  symbol: string;
  signal_type: string;
  cluster_id: number;
  anomaly_score: number;
  action: string;
  entry_price: number;
  raw_quantity: number;
  timestamp_utc: string;
  risk_approved: boolean;
  sized_quantity: number;
}

/** Error response from the server */
export interface ErrorResponse {
  error: string;
}
