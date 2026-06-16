#!/usr/bin/env bash
# Start the warm LibreOffice listener and prewarm it in the background so the web
# server can bind its port immediately (Render's health check needs an open port
# fast — blocking on prewarm first causes a port-scan timeout / failed deploy).
unoserver &

(
  printf 'warmup' > /tmp/warm.txt
  for _ in $(seq 1 30); do
    unoconvert --convert-to pdf /tmp/warm.txt /tmp/warm.pdf >/dev/null 2>&1 && { echo "unoserver ready (prewarmed)"; break; }
    sleep 1
  done
) &

exec gunicorn --bind 0.0.0.0:10000 --timeout 120 --workers 1 --threads 4 app:app
