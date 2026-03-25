#!/usr/bin/env bash
set -euo pipefail

# setup_shopify.sh — Shopifyストア開設後のセットアップ自動化
# Usage: ./setup_shopify.sh <store_domain> <api_key>
#   store_domain: YOUR-STORE.myshopify.com
#   api_key:      shpat_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

readonly SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
readonly HEALTH_URL="http://localhost:8788/health"
readonly PRODUCTS_URL="http://localhost:8788/products"
readonly KEYMASTER="$HOME/keymaster"

# ---- 引数チェック ----
if [[ $# -ne 2 ]]; then
    echo "Usage: $0 <store_domain> <api_key>" >&2
    echo "  store_domain: YOUR-STORE.myshopify.com" >&2
    echo "  api_key:      shpat_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" >&2
    exit 1
fi

STORE_DOMAIN="$1"
API_KEY="$2"

# 簡易バリデーション
if [[ ! "$STORE_DOMAIN" =~ \.myshopify\.com$ ]]; then
    echo "ERROR: store_domain は *.myshopify.com 形式で指定してください (got: $STORE_DOMAIN)" >&2
    exit 1
fi

if [[ ! "$API_KEY" =~ ^shpat_ ]]; then
    echo "ERROR: api_key は shpat_ で始まる Shopify Admin API トークンを指定してください" >&2
    exit 1
fi

echo "=== Akari Beads Shop - Shopify セットアップ ==="
echo "  store_domain: $STORE_DOMAIN"
echo "  api_key:      ${API_KEY:0:10}..."
echo ""

# ---- 1. Keymaster に実値を登録 ----
echo "[1/5] Keymaster に store_domain を登録..."
"$KEYMASTER/set_key.sh" shopify store_domain "$STORE_DOMAIN"

echo "[2/5] Keymaster に api_key を登録..."
"$KEYMASTER/set_key.sh" shopify api_key "$API_KEY"

# ---- 2. 登録確認 ----
echo "[3/5] 登録確認..."
GOT_DOMAIN="$("$KEYMASTER/get_key.sh" shopify store_domain 2>/dev/null)"
GOT_KEY="$("$KEYMASTER/get_key.sh" shopify api_key 2>/dev/null)"

if [[ "$GOT_DOMAIN" == "PLACEHOLDER" || -z "$GOT_DOMAIN" ]]; then
    echo "ERROR: store_domain の登録に失敗 (got: '$GOT_DOMAIN')" >&2
    exit 1
fi
if [[ "$GOT_KEY" == "PLACEHOLDER" || -z "$GOT_KEY" ]]; then
    echo "ERROR: api_key の登録に失敗 (got: PLACEHOLDER or empty)" >&2
    exit 1
fi
echo "  store_domain: $GOT_DOMAIN"
echo "  api_key:      ${GOT_KEY:0:10}..."
echo "  OK: PLACEHOLDER ではないことを確認"

# ---- 3. サービス再起動 ----
echo "[4/5] akari-beads-shop を再起動..."
sudo systemctl restart akari-beads-shop

# 起動待ち (最大 15 秒)
echo "  サービス起動を待機中..."
for i in $(seq 1 15); do
    if curl -sf "$HEALTH_URL" >/dev/null 2>&1; then
        break
    fi
    if [[ $i -eq 15 ]]; then
        echo "ERROR: サービスが 15 秒以内に起動しませんでした" >&2
        echo "  systemctl status akari-beads-shop で確認してください" >&2
        exit 1
    fi
    sleep 1
done

# ---- 4. ヘルスチェック ----
echo "[5/5] ヘルスチェック..."
HEALTH_RESPONSE="$(curl -s -w "\n%{http_code}" "$HEALTH_URL")"
HEALTH_BODY="$(echo "$HEALTH_RESPONSE" | head -n -1)"
HEALTH_CODE="$(echo "$HEALTH_RESPONSE" | tail -n 1)"

echo "  HTTP $HEALTH_CODE"
echo "$HEALTH_BODY" | python3 -m json.tool 2>/dev/null || echo "$HEALTH_BODY"

if [[ "$HEALTH_CODE" != "200" ]]; then
    echo "ERROR: /health が 200 を返しませんでした (got: $HEALTH_CODE)" >&2
    exit 1
fi

# ---- 5. 商品 API 疎通確認 ----
echo ""
echo "=== 商品 API 疎通確認 ==="
PRODUCTS_RESPONSE="$(curl -s -w "\n%{http_code}" "$PRODUCTS_URL")"
PRODUCTS_BODY="$(echo "$PRODUCTS_RESPONSE" | head -n -1)"
PRODUCTS_CODE="$(echo "$PRODUCTS_RESPONSE" | tail -n 1)"

echo "  HTTP $PRODUCTS_CODE"
echo "$PRODUCTS_BODY" | python3 -m json.tool 2>/dev/null || echo "$PRODUCTS_BODY"

if [[ "$PRODUCTS_CODE" == "200" ]]; then
    echo ""
    echo "=== セットアップ完了! ==="
    echo "  store: https://$STORE_DOMAIN"
    echo "  health: $HEALTH_URL"
    echo "  products: $PRODUCTS_URL"
else
    echo ""
    echo "WARNING: /products が $PRODUCTS_CODE を返しました。API キーの権限を確認してください。"
    echo "  Shopify 管理画面 → アプリ → カスタムアプリ → Admin API スコープに read_products があるか確認"
    exit 1
fi
