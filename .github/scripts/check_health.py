import sys
import json

lines = sys.stdin.read().strip().split("\n")
services = [json.loads(l) for l in lines if l.strip()]
not_ready = [
    s["Service"]
    for s in services
    if not (
        s.get("Health", "") == "healthy"
        or ("Health" not in s and s.get("State") == "running")
    )
]
healthy_count = len(services) - len(not_ready)
if not_ready:
    print(f"{healthy_count}/{len(services)} services ready (waiting: {', '.join(not_ready)})")
else:
    print(f"{healthy_count}/{len(services)} services ready")
sys.exit(0 if healthy_count >= len(services) - 1 else 1)
