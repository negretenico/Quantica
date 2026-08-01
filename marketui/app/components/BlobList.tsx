"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchIndex, dateFromFilename } from "../../lib/api";

interface BlobListProps {
  onSelectDate: (date: string) => void;
  selectedDate: string | null;
}

export default function BlobList({ onSelectDate, selectedDate }: BlobListProps) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["blobIndex"],
    queryFn: fetchIndex,
  });

  const dates = data?.blobs.map((b) => dateFromFilename(b.filename)) ?? [];

  if (isLoading) {
    return <p className="text-sm text-muted">Loading dates...</p>;
  }

  if (isError || dates.length === 0) {
    return (
      <div className="rounded-md border border-border bg-surface p-4 text-center text-sm text-muted">
        No data yet
      </div>
    );
  }

  return (
    <div className="flex flex-wrap gap-2">
      {dates.map((date) => (
        <button
          key={date}
          onClick={() => onSelectDate(date)}
          className={`rounded-md border px-3 py-1.5 text-sm transition-colors ${
            selectedDate === date
              ? "border-accent bg-accent-dim text-accent font-medium"
              : "border-border bg-surface text-muted hover:border-accent hover:text-foreground"
          }`}
        >
          {date}
        </button>
      ))}
    </div>
  );
}
