"use client";

import { useState } from "react";
import Markdown from "react-markdown";

const docLinks = [
  {
    title: "Performance",
    description: "Pipeline throughput, latency benchmarks, and capacity analysis",
    raw: "https://raw.githubusercontent.com/negretenico/Quantica/main/docs/PERFORMANCE.md",
  },
  {
    title: "Signal Detectors",
    description: "Overview of all signal detection strategies",
    raw: "https://raw.githubusercontent.com/negretenico/Quantica/main/docs/DETECTORS.md",
  },
  {
    title: "Aggressive Buyer/Seller Detector",
    description: "Detects aggressive directional buying or selling pressure",
    raw: "https://raw.githubusercontent.com/negretenico/Quantica/main/docs/detectors/aggressive-buyer-seller.md",
  },
  {
    title: "Large Trade Detector",
    description: "Identifies unusually large individual trades",
    raw: "https://raw.githubusercontent.com/negretenico/Quantica/main/docs/detectors/large-trade-detected.md",
  },
  {
    title: "Price Spike Detector",
    description: "Detects sudden price movements beyond normal volatility",
    raw: "https://raw.githubusercontent.com/negretenico/Quantica/main/docs/detectors/price-spike.md",
  },
  {
    title: "Running the Pipeline",
    description: "Start order and configuration for all modules",
    raw: "https://raw.githubusercontent.com/negretenico/Quantica/main/docs/RUNNING.md",
  },
];

export default function DocsPage() {
  const [activeDoc, setActiveDoc] = useState<string | null>(null);
  const [content, setContent] = useState<string>("");
  const [loading, setLoading] = useState(false);

  async function loadDoc(title: string, raw: string) {
    if (activeDoc === title) {
      setActiveDoc(null);
      return;
    }
    setLoading(true);
    setActiveDoc(title);
    try {
      const res = await fetch(raw);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setContent(await res.text());
    } catch {
      setContent("Failed to load document.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1 className="mb-2 text-2xl font-semibold">Documentation</h1>
      <p className="mb-8 text-muted">
        How the pipeline works — methodology, performance, and detector details.
      </p>

      <div className="grid gap-4">
        {docLinks.map(({ title, description, raw }) => (
          <div key={raw}>
            <button
              onClick={() => loadDoc(title, raw)}
              className="block w-full rounded-md border border-border bg-surface p-4 text-left transition-colors hover:border-accent"
            >
              <h2 className="mb-1 font-medium text-foreground">{title}</h2>
              <p className="text-sm text-muted">{description}</p>
            </button>
            {activeDoc === title && (
              <div className="mt-2 rounded-md border border-border bg-surface p-6">
                {loading ? (
                  <p className="text-muted">Loading...</p>
                ) : (
                  <div className="prose prose-invert prose-sm max-w-none">
                    <Markdown>{content}</Markdown>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
