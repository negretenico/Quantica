import sys
import os

_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))

# Add the repo root to sys.path so that the `shared` package is importable
# when tests are run from the marketdlq directory.
sys.path.insert(0, _repo_root)
