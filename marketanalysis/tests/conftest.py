import sys
import os

_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

# Add the repo root so that the `shared` package is importable.
sys.path.insert(0, _repo_root)

# Add shared/ so that `rabbitmq` package resolves (used by app.rabbit_client).
sys.path.insert(0, os.path.join(_repo_root, "shared"))

# Add the marketanalysis directory so app/model/analysis packages resolve.
sys.path.insert(0, os.path.join(_repo_root, "marketanalysis"))
