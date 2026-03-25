#!/usr/bin/env bash
set -euo pipefail

# Load Keymaster credentials from openclaw .env
if [[ -f ~/openclaw/.env ]]; then
    set -a
    source ~/openclaw/.env
    set +a
else
    echo "ERROR: ~/openclaw/.env not found" >&2
    exit 1
fi

if [[ -z "${AKARI_KEYMASTER_URL:-}" || -z "${AKARI_KEYMASTER_TOKEN:-}" ]]; then
    echo "ERROR: AKARI_KEYMASTER_URL or AKARI_KEYMASTER_TOKEN not set" >&2
    exit 1
fi

export AKARI_KEYMASTER_URL
export AKARI_KEYMASTER_TOKEN

# Shopify store domain (override via env or set here)
export SHOPIFY_STORE_DOMAIN="${SHOPIFY_STORE_DOMAIN:-}"
if [[ -z "${SHOPIFY_STORE_DOMAIN}" ]]; then
    echo "WARNING: SHOPIFY_STORE_DOMAIN not set. Set it before creating products." >&2
fi

cd "$(dirname "$0")"
exec uvicorn server:app --host 0.0.0.0 --port 8787
