"use client";

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-20">
      <div className="rounded-md border border-red/30 bg-red/5 p-6 text-center">
        <h2 className="mb-2 text-lg font-semibold text-red">
          Something went wrong
        </h2>
        <p className="mb-4 text-sm text-muted">{error.message}</p>
        <button
          onClick={reset}
          className="rounded-md border border-border bg-surface px-4 py-2 text-sm text-foreground transition-colors hover:border-accent"
        >
          Try again
        </button>
      </div>
    </div>
  );
}
