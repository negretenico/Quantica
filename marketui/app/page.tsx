"use client";

import { useState } from "react";
import HealthBadge from "./components/HealthBadge";
import BlobList from "./components/BlobList";
import Narrative from "./components/Narrative";

export default function FeedPage() {
  const [selectedDate, setSelectedDate] = useState<string | null>(null);

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
        <BlobList onSelectDate={setSelectedDate} selectedDate={selectedDate} />
      </section>

      {selectedDate && (
        <section>
          <h2 className="mb-3 text-sm font-medium text-muted uppercase tracking-wide">
            Narratives for {selectedDate}
          </h2>
          <Narrative date={selectedDate} />
        </section>
      )}
    </div>
  );
}
