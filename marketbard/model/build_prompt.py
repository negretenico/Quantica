def build_prompt(events):
    header = "You are a financial market storyteller. Summarize these events in a readable Markdown story:\n\n"
    event_lines = "\n".join([f"- {e['symbol']} {e['type']} {e['quantity']} @ {e['price']}" for e in events])
    return header + event_lines
