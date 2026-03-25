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

# Shopify store domain: fetch from Keymaster, fall back to env vars
SHOPIFY_STORE_DOMAIN="${SHOPIFY_STORE_DOMAIN:-}"
if [[ -z "${SHOPIFY_STORE_DOMAIN}" ]]; then
    SHOPIFY_STORE_DOMAIN="$(~/keymaster/get_key.sh shopify store_domain 2>/dev/null || true)"
fi
# Fall back to SHOPIFY_STORE from openclaw/.env if Keymaster returned empty or PLACEHOLDER
if [[ -z "${SHOPIFY_STORE_DOMAIN}" || "${SHOPIFY_STORE_DOMAIN}" == "PLACEHOLDER" ]]; then
    SHOPIFY_STORE_DOMAIN="${SHOPIFY_STORE:-}"
fi
export SHOPIFY_STORE_DOMAIN
if [[ -z "${SHOPIFY_STORE_DOMAIN}" ]]; then
    echo "WARNING: SHOPIFY_STORE_DOMAIN not set (Keymaster returned PLACEHOLDER). Set it before creating products." >&2
fi

cd "$(dirname "$0")"
exec uvicorn server:app --host 0.0.0.0 --port 8788
