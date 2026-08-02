"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchHealth } from "../../lib/api";

export default function HealthBadge() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["health"],
    queryFn: fetchHealth,
    refetchInterval: 30_000,
  });

  const status = isLoading ? "loading" : isError ? "error" : data?.status === "ok" ? "ok" : "error";

  const color =
    status === "ok"
      ? "bg-green/20 text-green border-green/30"
      : status === "error"
        ? "bg-red/20 text-red border-red/30"
        : "bg-border text-muted border-border";

  const label =
    status === "ok"
      ? "Server online"
      : status === "error"
        ? "Server offline"
        : "Checking...";

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${color}`}
    >
      <span
        className={`inline-block h-2 w-2 rounded-full ${
          status === "ok"
            ? "bg-green"
            : status === "error"
              ? "bg-red"
              : "bg-muted"
        }`}
      />
      {label}
    </span>
  );
}
