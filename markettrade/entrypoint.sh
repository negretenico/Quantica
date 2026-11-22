#!/bin/sh
set -e

# Docker Desktop on Windows mounts host volumes as root:root with 600 perms.
# Fix ownership so the non-root 'app' user can read/write the decisions dir.
if [ -d /app/decisions ]; then
  chown -R app:app /app/decisions
  chmod -R u+rwX,go+rX /app/decisions
fi

exec gosu app python run.py
