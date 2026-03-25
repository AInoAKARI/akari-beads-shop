# akari-beads-shop セットアップ手順 (きらたん向け)

**現状:** `shopify/store_domain` が PLACEHOLDER のため `/health` が 503、商品APIが全て 500 エラー。
以下の手順で解消できます。

---

## Step 1: Shopify ストアを開設する

1. https://www.shopify.com にアクセスし、新規ストアを作成
2. ストア名は `akari-beads` など分かりやすい名前にする

## Step 2: カスタムアプリを作成し API トークンを取得する

1. Shopify 管理画面 →「設定」→「アプリと販売チャネル」→「アプリを開発」
2. 「カスタムアプリを作成」をクリック
3. Admin API のアクセススコープで以下を許可:
   - `write_products` / `read_products`
   - `write_orders` / `read_orders`
4. アプリをインストールし、**Admin API アクセストークン** (`shpat_` で始まる文字列) を控える

## Step 3: myshopify.com ドメインを確認する

管理画面の URL が `https://admin.shopify.com/store/xxxxxxxx/...` なら、
store_domain は **`xxxxxxxx.myshopify.com`** です。

または:「設定」→「ドメイン」→「Shopify が管理するドメイン」欄で確認。

> カスタムドメインではなく `*.myshopify.com` 形式を使うこと（Shopify API の要件）

## Step 4: Keymaster に登録する

```bash
# store_domain を登録
~/keymaster/set_key.sh shopify store_domain "xxxxxxxx.myshopify.com"

# Admin API アクセストークンを登録
~/keymaster/set_key.sh shopify api_key "shpat_ここにトークンを貼る"
```

登録確認:
```bash
~/keymaster/get_key.sh shopify store_domain
# → xxxxxxxx.myshopify.com が返ること (PLACEHOLDER でないこと)

~/keymaster/get_key.sh shopify api_key
# → shpat_... が返ること (PLACEHOLDER でないこと)
```

## Step 5: サービスを再起動して /health 200 を確認する

```bash
sudo systemctl restart akari-beads-shop
```

ヘルスチェック:
```bash
curl -s http://localhost:8788/health | python3 -m json.tool
```

**OK の条件 (全て満たすこと):**
- HTTP ステータス: **200** (503 でないこと)
- `shopify_domain`: 設定した `xxxxxxxx.myshopify.com` が表示
- `keymaster`: `ok`

> 503 が返る場合は Step 4 の登録値を再確認し、もう一度再起動してください。

---

## (任意) Step 6: Webhook を設定する

注文通知を受け取りたい場合は以下を実施。現時点では server.py に webhook エンドポイントが未実装のため、先にコード追加が必要です。

1. Webhook シークレットを Keymaster に登録:
   ```bash
   ~/keymaster/set_key.sh shopify webhook_secret "ここにシークレットを貼る"
   ```
2. server.py に webhook エンドポイントを追加する
3. Shopify 管理画面 →「設定」→「通知」→「Webhook」で URL を登録

---

## Vault 登録状況チェックリスト

| Vault パス | 必須 | 現状 |
|---|---|---|
| `shopify/store_domain` | Yes | PLACEHOLDER → Step 4 で設定 |
| `shopify/api_key` | Yes | PLACEHOLDER → Step 4 で設定 |
| `shopify/webhook_secret` | No (Step 6) | 未登録 → 必要時に設定 |
