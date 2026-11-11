"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchPortfolio } from "../../lib/api";
import type { PortfolioState } from "../../lib/types";

function fmt(n: number, decimals = 2): string {
  return n.toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function PnlText({ value }: { value: number }) {
  const color =
    value > 0 ? "text-green" : value < 0 ? "text-red" : "text-muted";
  const prefix = value > 0 ? "+" : "";
  return <span className={color}>{prefix}{fmt(value)}</span>;
}

function SummaryCards({ state }: { state: PortfolioState }) {
  const positionCount = Object.keys(state.positions).length;
  const unrealizedPnl = Object.entries(state.positions).reduce(
    (sum, [, pos]) => sum + pos.quantity * (pos.avg_entry_price - pos.avg_entry_price),
    0,
  );
  const totalPnl = state.realized_pnl + unrealizedPnl;
  const returnPct =
    state.starting_balance > 0
      ? (totalPnl / state.starting_balance) * 100
      : 0;

  const cards = [
    { label: "Cash", value: `$${fmt(state.cash)}` },
    { label: "Positions", value: String(positionCount) },
    {
      label: "Realized P&L",
      node: <PnlText value={state.realized_pnl} />,
    },
    {
      label: "Return",
      node: <PnlText value={returnPct} />,
      suffix: "%",
    },
  ];

  return (
    <div data-testid="summary-cards" className="mb-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
      {cards.map((c) => (
        <div
          key={c.label}
          className="rounded-md border border-border bg-surface p-4"
        >
          <p className="text-xs text-muted">{c.label}</p>
          <p className="mt-1 text-lg font-semibold">
            {c.node ?? c.value}
            {c.suffix ?? ""}
          </p>
        </div>
      ))}
    </div>
  );
}

function PositionsTable({ state }: { state: PortfolioState }) {
  const entries = Object.entries(state.positions);

  if (entries.length === 0) {
    return (
      <p className="text-muted" data-testid="no-positions">No open positions.</p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-md border border-border">
      <table className="w-full text-sm" data-testid="positions-table">
        <thead>
          <tr className="border-b border-border bg-surface text-left text-muted">
            <th className="px-4 py-2">Symbol</th>
            <th className="px-4 py-2 text-right">Quantity</th>
            <th className="px-4 py-2 text-right">Avg Entry</th>
            <th className="px-4 py-2 text-right">Cost Basis</th>
            <th className="px-4 py-2">Opened</th>
          </tr>
        </thead>
        <tbody>
          {entries.map(([symbol, pos]) => (
            <tr
              key={symbol}
              className="border-b border-border last:border-0 hover:bg-surface/50"
            >
              <td className="px-4 py-2 font-medium">{symbol}</td>
              <td className="px-4 py-2 text-right font-mono">
                {fmt(pos.quantity, 6)}
              </td>
              <td className="px-4 py-2 text-right font-mono">
                ${fmt(pos.avg_entry_price)}
              </td>
              <td className="px-4 py-2 text-right font-mono">
                ${fmt(pos.quantity * pos.avg_entry_price)}
              </td>
              <td className="px-4 py-2 text-xs text-muted">
                {new Date(pos.opened_at).toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function PortfolioPage() {
  const { data: state, isLoading, isError } = useQuery({
    queryKey: ["portfolio"],
    queryFn: fetchPortfolio,
    refetchInterval: 5_000,
  });

  return (
    <div>
      <h1 className="mb-2 text-2xl font-semibold">Paper Portfolio</h1>
      <p className="mb-8 text-muted">
        Live paper trading portfolio managed by the markettrade worker.
      </p>

      <div className="mb-6 rounded-md border border-orange/30 bg-orange/5 p-4 text-sm text-orange">
        <strong>Paper Trading:</strong> All positions are simulated. No real
        funds are at risk. Starting balance: $100.
      </div>

      {isLoading && (
        <p className="text-muted" data-testid="loading">Loading portfolio...</p>
      )}

      {isError && (
        <div
          data-testid="error-state"
          className="rounded-md border border-border bg-surface p-8 text-center text-muted"
        >
          Could not load portfolio. The markettrade worker may not have started
          yet.
        </div>
      )}

      {state && (
        <>
          <SummaryCards state={state} />

          <h2 className="mb-4 text-lg font-semibold">Open Positions</h2>
          <PositionsTable state={state} />

          <p className="mt-6 text-xs text-muted" data-testid="updated-at">
            Last updated: {new Date(state.updated_at).toLocaleString()}
          </p>
        </>
      )}
    </div>
  );
}
