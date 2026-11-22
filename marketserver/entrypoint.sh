#!/bin/sh
set -e

# Docker Desktop on Windows mounts host volumes as root:root with 600 perms.
# Fix ownership so the non-root 'app' user can read the data dirs.
for dir in /data/bard /data/trade; do
  if [ -d "$dir" ]; then
    chown -R app:app "$dir"
    chmod -R u+rwX,go+rX "$dir"
  fi
done

exec gosu app python run.py
