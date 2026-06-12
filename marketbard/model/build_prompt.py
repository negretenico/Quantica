def build_prompt(events):
    header = "You are a financial market storyteller. Summarize these events in a readable Markdown story, Be sure to make it quirky and personable simulate Joey Tribianni from friends:\n\n"
    if len(events) == 1 and isinstance(events[0], list):
        events = events[0]
    event_lines = "\n".join([
        f"- {e['symbol']} {e.get('type', '')} {e.get('quantity', '')} @ {e.get('price', '')}"
        for e in events
    ])
    return header + event_lines


def build_window_prompt(events: list, metrics: dict) -> str:
    """
    Prompt for a single 10-minute window. Deterministic metrics are pre-computed
    and injected here so the model never has to calculate them — preventing
    nondeterminism in volume/price figures.
    """
    header = (
        "You are a financial market analyst. Summarize the following 10-minute market window. "
        "Return a SHORT narrative summary (2-3 sentences max) and a categorical classification. "
        "Be concise — your response must be under 150 tokens.\n\n"
    )
    metrics_section = (
        f"Window: {metrics['window_start']}\n"
        f"Volume: {metrics['volume']:.4f}\n"
        f"Price movement: {metrics['price_movement']:.4f}\n"
        f"Anomaly count: {metrics['anomaly_count']}\n\n"
    )
    event_lines = "\n".join([
        f"- {e.get('symbol', '')} {e.get('type', '')} {e.get('quantity', '')} @ {e.get('price', '')}"
        + (" [ANOMALY]" if e.get("anomaly_score") is not None else "")
        for e in events
    ])
    return header + metrics_section + event_lines


def build_synthesis_prompt(summaries: list) -> str:
    """
    Prompt for the end-of-day synthesis pass. Takes all window summaries
    accumulated in SummaryBuffer and asks the model to produce a cohesive
    all-day narrative. Context size is bounded by MAX_SUMMARY_BUFFER upstream.
    """
    header = (
        "You are a financial market analyst. "
        "Using the 10-minute window summaries below from today's trading session, "
        "write a cohesive all-day market narrative in Markdown. Be serious and professional.\n\n"
    )
    summary_lines = "\n\n".join([
        f"**{s['window_start']}** [{s['category']}]\n"
        f"{s['narrative_summary']}\n"
        f"Volume: {s['metrics']['volume']:.4f} | "
        f"Price Δ: {s['metrics']['price_movement']:.4f} | "
        f"Anomalies: {s['metrics']['anomaly_count']}"
        for s in summaries
    ])
    return header + summary_lines
