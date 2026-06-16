#!/usr/bin/env bash
set -e

# Start the persistent LibreOffice listener in the background so each
# conversion skips LibreOffice's cold start.
unoserver &

# Best-effort prewarm: wait for unoserver to come up, then convert a tiny
# document so the first real request doesn't pay first-document load cost.
printf 'warmup' > /tmp/warm.txt
for _ in $(seq 1 30); do
  if unoconvert --convert-to pdf /tmp/warm.txt /tmp/warm.pdf >/dev/null 2>&1; then
    echo "unoserver ready (prewarmed)"
    break
  fi
  sleep 1
done

exec gunicorn --bind 0.0.0.0:10000 --timeout 120 --workers 1 --threads 4 app:app
