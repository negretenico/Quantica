import sys
import os

# Add the repo root to sys.path so that the `shared` package is importable
# when tests are run from the marketbard directory.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
