#!/usr/bin/env bash
set -eu
id=org.pairthing.desktop
flatpak run --command=sh "$id" -ec 'ldd /app/bin/pairthing | grep libwebkit2gtk-4.1; /app/bin/runtime/syncthing --version'
flatpak run "$id" &
pid=$!
trap 'flatpak kill "$id" || true' EXIT
for i in $(seq 1 60); do
  kill -0 "$pid"
  if xdotool search --onlyvisible --name '^Pairthing$' >/dev/null && pgrep -f '^/app/bin/runtime/pairthing-controller/pairthing-controller ' >/dev/null; then
    exit 0
  fi
  sleep 1
done
exit 1
