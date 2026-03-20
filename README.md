# Akari Beads Shop

Shopify商品登録API for きらきらあかりん食堂ビーズショップ。

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | ヘルスチェック |
| GET | `/products` | 商品一覧取得 |
| POST | `/products/create` | 商品作成（画像+情報） |
| POST | `/webhooks/orders/create` | Shopify注文Webhook受信 |

## POST /products/create

- `title` (form): 商品名
- `description` (form): 説明
- `price` (form): 価格
- `image` (file): 商品画像

## Setup

```bash
chmod +x start_beads_shop.sh
./start_beads_shop.sh
```

環境変数 `AKARI_KEYMASTER_URL`, `AKARI_KEYMASTER_TOKEN` は `~/openclaw/.env` から読み込み。
`SHOPIFY_STORE` は別途設定が必要。

## Shopify Webhook Setup

1. Shopify Admin で `Settings` > `Notifications` > `Webhooks` を開く
2. Topic は `Order creation` を選ぶ
3. Delivery URL は `https://<your-host>/webhooks/orders/create` を設定する
4. Format は `JSON`
5. Webhook secret は Keymaster に `service=shopify`, `key_name=webhook_secret` で保存する
6. Telegram Bot Token は Keymaster に `service=telegram`, `key_name=api_key` で保存する
7. Telegram Chat ID は Keymaster に `service=telegram`, `key_name=chat_id` で保存する
   Keymaster に無い場合は環境変数 `TELEGRAM_CHAT_ID` でも可
8. Notion Integration Token は Keymaster に `service=notion`, `key_name=api_key` で保存する
9. Notion 側で企画書ページ `329f46dbdd8d815aa79be904bde55141` に integration を共有する

Webhook を受けると、署名を `X-Shopify-Hmac-Sha256` で検証し、Telegram に売上通知を送り、Notion 企画書ページ配下へ売上ログ子ページを作成します。

## Docker

```bash
docker build -t akari-beads-shop .
docker run -p 8787:8787 -e AKARI_KEYMASTER_URL=... -e AKARI_KEYMASTER_TOKEN=... -e SHOPIFY_STORE=... akari-beads-shop
```
