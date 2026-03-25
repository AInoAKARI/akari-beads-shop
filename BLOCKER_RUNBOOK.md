# BLOCKER_RUNBOOK: store_domain PLACEHOLDER 解除手順

> **前提**: Shopify ストアが開設済みで `*.myshopify.com` ドメインが確定していること。
> ドメインの確認方法は [REPORT.md「きらたん向け」セクション](REPORT.md) を参照。

## 手順（3 コマンド + healthcheck）

```bash
# ---- Step 1: Keymaster に store_domain を登録 ----
~/keymaster/set_key.sh shopify store_domain "YOUR-STORE.myshopify.com"

# ---- Step 2: 登録結果を確認 ----
~/keymaster/get_key.sh shopify store_domain
# → "YOUR-STORE.myshopify.com" が返ればOK（PLACEHOLDER でないこと）

# ---- Step 3: サービス再起動 ----
# start_beads_shop.sh は Keymaster から値を自動取得するので、
# systemd を止めてからスクリプト経由で起動する。
sudo systemctl stop akari-beads-shop
~/akari-beads-shop/start_beads_shop.sh

# ---- Step 4: healthcheck ----
curl -s http://localhost:8788/health | python3 -m json.tool
# → "shopify_domain": "YOUR-STORE.myshopify.com" かつ HTTP 200 なら完了
```

## systemctl restart ではダメな理由

`akari-beads-shop.service` の `ExecStart` は `uvicorn server:app` を直接実行する。
`SHOPIFY_STORE_DOMAIN` は `EnvironmentFile` (`openclaw/.env`) からしか読まれず、
Keymaster fetch ロジック（`start_beads_shop.sh` L24-31）を通らない。

**対策（いずれか）:**
- **A（推奨・上記手順）**: `systemctl stop` → `start_beads_shop.sh` で起動
- **B（恒久対応）**: systemd unit の `ExecStart` を `start_beads_shop.sh` に変更する

## 確認チェックリスト

- [ ] `get_key.sh shopify store_domain` が `PLACEHOLDER` でない
- [ ] `curl http://localhost:8788/health` が HTTP 200
- [ ] レスポンスの `shopify_domain` に正しいドメインが表示されている
- [ ] `curl http://localhost:8788/products` が 500 でなく応答する（API キーも設定済みの場合）

## 注意

- `api_key` も未登録の場合は `/health` の `keymaster` が `error` になる。その場合は追加で:
  ```bash
  ~/keymaster/set_key.sh shopify api_key "shpat_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  ```
- ポートは **8788**（Notion の 8787 は誤り）
