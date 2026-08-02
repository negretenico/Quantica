import sys
import os

_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

# Add the repo root to sys.path so that the `shared` package is importable
# when tests are run from the markettrade directory.
sys.path.insert(0, _repo_root)

# Add the marketrisk project directory so `from marketrisk.risk.engine import ...` resolves
# (nested package layout: marketrisk/marketrisk/risk/engine.py).
sys.path.insert(0, os.path.join(_repo_root, "marketrisk"))
