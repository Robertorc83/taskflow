#!/bin/sh
# Runs from the nginx image's /docker-entrypoint.d before nginx starts (CR-012).
# TLS is the default and fails closed: with NGINX_TLS=true and no certificate, the container exits.
set -eu

CERTS=/etc/nginx/certs
case "${NGINX_TLS:-true}" in
  true)
    if [ ! -r "$CERTS/tls.crt" ] || [ ! -r "$CERTS/tls.key" ]; then
      echo "NGINX_TLS=true but $CERTS/tls.crt and tls.key are not both mounted." >&2
      echo "Mount a certificate, or set NGINX_TLS=false when TLS ends upstream." >&2
      exit 1
    fi
    server=https.conf
    ;;
  false) server=http.conf ;;
  *)
    echo "NGINX_TLS must be true or false, got '${NGINX_TLS}'." >&2
    exit 1
    ;;
esac

ln -sf "/etc/nginx/servers/$server" /etc/nginx/conf.d/default.conf
echo "select-config: serving $server"
