# Akari Beads Shop

Shopify商品登録API for きらきらあかりん食堂ビーズショップ。

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | ヘルスチェック |
| GET | `/products` | 商品一覧取得 |
| POST | `/products/create` | 商品作成（画像+情報） |

## POST /products/create

- `title` (form): 商品名
- `description` (form): 説明
- `price` (form): 価格
- `image` (file, optional): 商品画像

## Setup

```bash
chmod +x start_beads_shop.sh
./start_beads_shop.sh
```

環境変数 `AKARI_KEYMASTER_URL`, `AKARI_KEYMASTER_TOKEN` は `~/openclaw/.env` から読み込み。
`SHOPIFY_STORE` は別途設定が必要。

## Docker

```bash
docker build -t akari-beads-shop .
docker run -p 8787:8787 \
  -e AKARI_KEYMASTER_URL=... \
  -e AKARI_KEYMASTER_TOKEN=... \
  -e SHOPIFY_STORE=... \
  akari-beads-shop
```
