"use client";

import { useQuery } from "@tanstack/react-query";
import Markdown from "react-markdown";
import { fetchBlob } from "../../lib/api";

interface NarrativeProps {
  date: string;
}

export default function Narrative({ date }: NarrativeProps) {
  const { data: records, isLoading, isError } = useQuery({
    queryKey: ["blob", date],
    queryFn: () => fetchBlob(date),
    enabled: !!date,
  });

  if (isLoading) {
    return <p className="text-sm text-muted">Loading narratives...</p>;
  }

  if (isError) {
    return (
      <div className="rounded-md border border-red/30 bg-red/5 p-4 text-sm text-red">
        Failed to load narratives for {date}.
      </div>
    );
  }

  if (!records || records.length === 0) {
    return (
      <div className="rounded-md border border-border bg-surface p-4 text-center text-sm text-muted">
        No narratives for {date}.
      </div>
    );
  }

  return (
    <div className="grid gap-4">
      {records.map((record, idx) => (
        <article
          key={`${date}-${idx}`}
          className="rounded-md border border-border bg-surface p-6"
        >
          <div className="prose prose-invert prose-sm max-w-none">
            <Markdown>{record.content}</Markdown>
          </div>
          <p className="mt-4 text-xs text-muted">
            Written at {new Date(record.written_at).toLocaleString()}
          </p>
        </article>
      ))}
    </div>
  );
}
