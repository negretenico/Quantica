"use client";

import { Suspense } from "react";
import { useSuspenseQuery } from "@tanstack/react-query";
import Markdown from "react-markdown";
import { fetchBlob } from "../../lib/api";

interface NarrativeProps {
  date: string;
}

function NarrativeContent({ date }: NarrativeProps) {
  const { data: records } = useSuspenseQuery({
    queryKey: ["blob", date],
    queryFn: () => fetchBlob(date),
  });

  if (records.length === 0) {
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

export default function Narrative({ date }: NarrativeProps) {
  return (
    <Suspense
      fallback={<p className="text-sm text-muted">Loading narratives...</p>}
    >
      <NarrativeContent date={date} />
    </Suspense>
  );
}
