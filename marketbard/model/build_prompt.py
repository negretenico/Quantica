def build_prompt(events):
    header = "You are a financial market storyteller. Summarize these events in a readable Markdown story, Be sure to make it quirky and personable simulate Joey Tribianni from friends:\n\n"
    # flatten if needed
    if len(events) == 1 and isinstance(events[0], list):
        events = events[0]

    event_lines = "\n".join([
        f"- {e['symbol']} {e.get('type', '')} {e.get('quantity', '')} @ {e.get('price', '')}"
        for e in events
    ])
    return header + event_lines
