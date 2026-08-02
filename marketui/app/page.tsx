"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchIndex, dateFromFilename } from "../lib/api";
import { useDateSelector } from "../lib/useDateSelector";
import HealthBadge from "./components/HealthBadge";
import Narrative from "./components/Narrative";

export default function FeedPage() {
  const { data: dates = [] } = useQuery({
    queryKey: ["blobIndex"],
    queryFn: fetchIndex,
    select: (data) => data.blobs.map((b) => dateFromFilename(b.filename)),
  });

  const { activeDate, toggle } = useDateSelector(dates);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="mb-1 text-2xl font-semibold">Market Feed</h1>
          <p className="text-muted">
            Live signals, anomalies, and narratives from the Quantica pipeline.
          </p>
        </div>
        <HealthBadge />
      </div>

      <section className="mb-6">
        <h2 className="mb-3 text-sm font-medium text-muted uppercase tracking-wide">
          Available Dates
        </h2>
        {dates.length === 0 ? (
          <div className="rounded-md border border-border bg-surface p-4 text-center text-sm text-muted">
            No data yet
          </div>
        ) : (
          <div className="flex flex-wrap gap-2">
            {dates.map((date) => (
              <button
                key={date}
                onClick={() => toggle(date)}
                className={`rounded-md border px-3 py-1.5 text-sm transition-colors ${
                  activeDate === date
                    ? "border-accent bg-accent-dim text-accent font-medium"
                    : "border-border bg-surface text-muted hover:border-accent hover:text-foreground"
                }`}
              >
                {date}
              </button>
            ))}
          </div>
        )}
      </section>

      {activeDate && (
        <section>
          <h2 className="mb-3 text-sm font-medium text-muted uppercase tracking-wide">
            Narratives for {activeDate}
          </h2>
          <Narrative date={activeDate} />
        </section>
      )}
    </div>
  );
}
