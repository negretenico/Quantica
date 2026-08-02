import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import HealthBadge from "./HealthBadge";

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("HealthBadge", () => {
  it("shows 'Checking...' while loading", () => {
    vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise(() => {})); // never resolves
    render(<HealthBadge />, { wrapper });
    expect(screen.getByText("Checking...")).toBeInTheDocument();
  });

  it("shows 'Server online' when health is ok", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ status: "ok" }),
    } as Response);

    render(<HealthBadge />, { wrapper });
    expect(await screen.findByText("Server online")).toBeInTheDocument();
  });

  it("shows 'Server offline' when fetch fails", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("Network error"));

    render(<HealthBadge />, { wrapper });
    expect(await screen.findByText("Server offline")).toBeInTheDocument();
  });

  it("shows 'Server offline' when status is not ok", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ status: "degraded" }),
    } as Response);

    render(<HealthBadge />, { wrapper });
    expect(await screen.findByText("Server offline")).toBeInTheDocument();
  });
});
