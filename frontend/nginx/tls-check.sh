#!/usr/bin/env bash
# Black-box check of the web image's TLS behavior (CR-012). Needs Docker, curl and openssl.
# Usage: frontend/nginx/tls-check.sh   (or `make tls-check`)
set -euo pipefail

IMAGE=taskmanager-web:tls-check
NAME=taskmanager-web-tls-check
HTTP_PORT=18080
HTTPS_PORT=18443
FRONTEND_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CERTS="$(mktemp -d)"
FAILURES=0

cleanup() { docker rm -f "$NAME" >/dev/null 2>&1 || true; rm -rf "$CERTS"; }
trap cleanup EXIT

check() {  # check <description> <command...>
  local description=$1
  shift
  if "$@" >/dev/null 2>&1; then echo "  ok   $description"; else echo "  FAIL $description"; FAILURES=$((FAILURES + 1)); fi
}

headers() { curl -sS -o /dev/null -D - "$@"; }
export -f headers

refuses_to_start() {  # the container must exit on its own, with a non-zero status
  docker rm -f "$NAME" >/dev/null 2>&1 || true
  docker run -d --name "$NAME" --add-host api:127.0.0.1 "$IMAGE" >/dev/null
  for _ in $(seq 1 50); do
    if [ "$(docker inspect -f '{{.State.Running}}' "$NAME")" = false ]; then
      [ "$(docker inspect -f '{{.State.ExitCode}}' "$NAME")" != 0 ]
      return
    fi
    sleep 0.2
  done
  return 1
}

run_web() {  # run_web <extra docker args...>
  docker rm -f "$NAME" >/dev/null 2>&1 || true
  # nginx resolves the `api` upstream at startup; point it anywhere so the container boots alone.
  docker run -d --name "$NAME" --add-host api:127.0.0.1 \
    -p "127.0.0.1:$HTTP_PORT:80" -p "127.0.0.1:$HTTPS_PORT:443" "$@" "$IMAGE" >/dev/null
  for _ in $(seq 1 50); do
    curl -s -o /dev/null "http://127.0.0.1:$HTTP_PORT/healthz" && return 0
    sleep 0.2
  done
  docker logs "$NAME" >&2
  return 1
}

echo "Building $IMAGE"
docker build -q -t "$IMAGE" "$FRONTEND_DIR" >/dev/null

echo "Fail closed: TLS is the image default, and it refuses to start without a certificate"
check "exits non-zero with no certificate mounted" refuses_to_start

echo "TLS on (certificate mounted)"
openssl req -x509 -newkey rsa:2048 -nodes -days 1 -subj "/CN=localhost" \
  -keyout "$CERTS/tls.key" -out "$CERTS/tls.crt" 2>/dev/null
chmod 644 "$CERTS/tls.key"
run_web -v "$CERTS:/etc/nginx/certs:ro"
check "HTTP redirects to HTTPS" \
  bash -c "headers 'http://127.0.0.1:$HTTP_PORT/tasks?page=2' | grep -qiE '^location: https://[^/]+/tasks\?page=2'"
check "health check answers on plain HTTP (not redirected, not the SPA fallback)" \
  bash -c "curl -fsS 'http://127.0.0.1:$HTTP_PORT/healthz' | grep -qx ok"
check "HTTPS serves the app" curl -fsSk "https://127.0.0.1:$HTTPS_PORT/"
check "HTTPS sends HSTS" \
  bash -c "headers -k 'https://127.0.0.1:$HTTPS_PORT/' | grep -qi '^strict-transport-security: max-age='"
check "HTTPS keeps the security headers" \
  bash -c "headers -k 'https://127.0.0.1:$HTTPS_PORT/assets/missing.js' | grep -qi '^content-security-policy:'"
check "TLS 1.2 is accepted" \
  curl -fsSk --tlsv1.2 --tls-max 1.2 "https://127.0.0.1:$HTTPS_PORT/"
check "TLS 1.1 is refused" \
  bash -c "! curl -sk --tlsv1.1 --tls-max 1.1 'https://127.0.0.1:$HTTPS_PORT/'"

echo "TLS off (NGINX_TLS=false, e.g. local compose or TLS terminated upstream)"
run_web -e NGINX_TLS=false
check "HTTP serves the app" curl -fsS "http://127.0.0.1:$HTTP_PORT/"
check "plain HTTP never sends HSTS" \
  bash -c "! headers 'http://127.0.0.1:$HTTP_PORT/' | grep -qi '^strict-transport-security:'"
check "plain HTTP keeps the security headers" \
  bash -c "headers 'http://127.0.0.1:$HTTP_PORT/' | grep -qi '^content-security-policy:'"

if [ "$FAILURES" -gt 0 ]; then echo "$FAILURES check(s) failed"; exit 1; fi
echo "All TLS checks passed"
