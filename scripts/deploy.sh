#!/usr/bin/env sh
# Dispara redeploy no Easypanel (não é automático via git push neste projeto).
set -eu

DEPLOY_URL="http://3.210.217.206:3000/api/deploy/6b32fc53ef703684f8b11416463a3bccd922af5c82959ea3"

echo "Disparando deploy no Easypanel..."
response="$(curl -sS -w "\n%{http_code}" -X POST "$DEPLOY_URL")"
body="$(printf '%s' "$response" | sed '$d')"
code="$(printf '%s' "$response" | tail -n 1)"

printf '%s\n' "$body"
if [ "$code" != "200" ]; then
  echo "Deploy falhou (HTTP $code)" >&2
  exit 1
fi
echo "Deploy acionado (HTTP $code)."
