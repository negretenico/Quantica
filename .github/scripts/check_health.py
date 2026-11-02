import sys
import json

lines = sys.stdin.read().strip().split("\n")
services = [json.loads(l) for l in lines if l.strip()]

# Services with a healthcheck must be "healthy".
# Services without a healthcheck are ignored (they're infra or non-essential).
checked = [s for s in services if s.get("Health")]
not_ready = [s["Service"] for s in checked if s["Health"] != "healthy"]
ready_count = len(checked) - len(not_ready)

if not_ready:
    print(f"{ready_count}/{len(checked)} health-checked services ready (waiting: {', '.join(not_ready)})")
else:
    print(f"{ready_count}/{len(checked)} health-checked services ready")

sys.exit(0 if not not_ready else 1)
