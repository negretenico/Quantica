const docLinks = [
  {
    title: "Performance",
    description: "Pipeline throughput, latency benchmarks, and capacity analysis",
    href: "https://github.com/negretenico/Quantica/blob/main/docs/PERFORMANCE.md",
  },
  {
    title: "Signal Detectors",
    description: "Overview of all signal detection strategies",
    href: "https://github.com/negretenico/Quantica/blob/main/docs/DETECTORS.md",
  },
  {
    title: "Aggressive Buyer/Seller Detector",
    description: "Detects aggressive directional buying or selling pressure",
    href: "https://github.com/negretenico/Quantica/blob/main/docs/detectors/aggressive-buyer-seller.md",
  },
  {
    title: "Large Trade Detector",
    description: "Identifies unusually large individual trades",
    href: "https://github.com/negretenico/Quantica/blob/main/docs/detectors/large-trade-detected.md",
  },
  {
    title: "Price Spike Detector",
    description: "Detects sudden price movements beyond normal volatility",
    href: "https://github.com/negretenico/Quantica/blob/main/docs/detectors/price-spike.md",
  },
  {
    title: "Running the Pipeline",
    description: "Start order and configuration for all modules",
    href: "https://github.com/negretenico/Quantica/blob/main/docs/RUNNING.md",
  },
];

export default function DocsPage() {
  return (
    <div>
      <h1 className="mb-2 text-2xl font-semibold">Documentation</h1>
      <p className="mb-8 text-muted">
        How the pipeline works — methodology, performance, and detector details.
      </p>

      <div className="grid gap-4">
        {docLinks.map(({ title, description, href }) => (
          <a
            key={href}
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="block rounded-md border border-border bg-surface p-4 transition-colors hover:border-accent"
          >
            <h2 className="mb-1 font-medium text-foreground">{title}</h2>
            <p className="text-sm text-muted">{description}</p>
          </a>
        ))}
      </div>
    </div>
  );
}
