# akari-beads-shop 調査レポート

## ブロッカー (2026-03-25 17:50 JST 再確認)

| # | 項目 | 状態 | 詳細 |
|---|------|------|------|
| 1 | `shopify/store_domain` が PLACEHOLDER | **未解決** | `~/keymaster/get_key.sh shopify store_domain` → `PLACEHOLDER`（2026-03-25 確認）。実値が登録されるまで商品API は 500、`/health` は 503 を返す |
| 2 | `shopify/api_key` が PLACEHOLDER | **未解決** | `~/keymaster/get_key.sh shopify api_key` → `PLACEHOLDER`（2026-03-25 確認）。Admin API トークンも未登録のため、ドメイン設定だけでは解消しない |
| 3 | Shopify ストア未開設（推定） | **未解決** | store_domain / api_key が両方 PLACEHOLDER → ストア自体が未作成の可能性が高い |
| 4 | 稼働中サーバーが古いコードのまま | **解決済み (2026-03-25)** | 旧 PID 515 は消滅。現在は PID 1067583 (2026-03-25 06:05 起動) が最新 `server.py` を配信中。`GET /` → 200、`/health` → `{"service":"ok","keymaster":"ok","shopify_domain":"dandan-brothers.myshopify.com"}` (HTTP 200)。systemd unit の `WorkingDirectory=/home/kawaii_ai_office/akari-beads-shop`、`ExecStart=.../start_beads_shop.sh` ともに正しいパスを確認済み |
| 5 | systemd unit が `start_beads_shop.sh` を経由していない | **解決済み (2026-03-25)** | `ExecStart=/home/kawaii_ai_office/akari-beads-shop/start_beads_shop.sh` を確認。Keymaster domain lookup を含むスクリプト経由で起動されている。`EnvironmentFile` は不使用（`start_beads_shop.sh` 自身が `~/openclaw/.env` を source する） |

**最短解除パス:** Shopify ストア開設 → Keymaster に store_domain + api_key を登録 → systemd unit 修正 or サービス再起動 → `/health` が 200 を返すことを確認

### きらたんが Shopify ストアを開設した直後に実行すべきコマンド一覧

Shopify 管理画面で (a) `*.myshopify.com` ドメイン、(b) カスタムアプリの Admin API アクセストークン を取得済みの前提。

```bash
# ---- 1. Keymaster に実値を登録 ----
~/keymaster/set_key.sh shopify store_domain "YOUR-STORE.myshopify.com"
~/keymaster/set_key.sh shopify api_key "shpat_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# ---- 2. 登録確認（PLACEHOLDER でないこと） ----
~/keymaster/get_key.sh shopify store_domain
~/keymaster/get_key.sh shopify api_key

# ---- 3. サービス再起動（最新 server.py を反映） ----
sudo systemctl restart akari-beads-shop

# ---- 4. ヘルスチェック ----
curl -s http://localhost:8788/health | python3 -m json.tool
# 期待値: keymaster=ok, shopify_domain=YOUR-STORE.myshopify.com, HTTP 200

# ---- 5. 商品 API 疎通確認 ----
curl -s http://localhost:8788/products | python3 -m json.tool
# 期待値: {"products": [], "count": 0} （商品未登録なら空配列）
```

> **注意:** 手順 3 で再起動しても `/health` が旧レスポンス (`{"status":"ok"}`) のままの場合、systemd unit の `WorkingDirectory` が正しいか、または `server.py` の変更がディスク上に保存されているか確認すること。`systemctl cat akari-beads-shop` で設定を確認できる。

---

## SHOPIFY_STORE_DOMAIN 設定状況 (2026-03-25)

### start_beads_shop.sh の挙動
- `~/openclaw/.env` から Keymaster 認証情報 (`AKARI_KEYMASTER_URL`, `AKARI_KEYMASTER_TOKEN`) を読み込む
- `SHOPIFY_STORE_DOMAIN` は環境変数からの注入を期待（デフォルト: 空文字列）
- 未設定時は WARNING を出すが、サーバー起動は続行する
- Keymaster 経由での自動取得ロジックあり（`get_key.sh shopify store_domain` を呼び出し、PLACEHOLDER や空の場合は `SHOPIFY_STORE` env にフォールバック）

### Keymaster 問い合わせ結果
```
$ ~/keymaster/get_key.sh shopify store_domain
PLACEHOLDER
```
- `PLACEHOLDER` が返却された → Keymaster にキーは登録されているが、実値が未設定（プレースホルダーのまま）

### 補足: ポート
- `start_beads_shop.sh` は `--port 8788` で起動（commit 65295ee 以降統一済み）

### 推奨アクション
1. Keymaster に `shopify store_domain` の実値を登録する
2. `start_beads_shop.sh` 内で Keymaster から `SHOPIFY_STORE_DOMAIN` を取得するロジックを追加するか、`.env` 経由で注入する仕組みを整備する
3. ポート番号を `8788` に修正する（要確認）

### Vault に正しい store_domain を登録する手順

現在 `~/keymaster/get_key.sh shopify store_domain` は `PLACEHOLDER` を返しており、実値が未登録です。
以下の手順で正しい値を登録してください。

1. Shopify 管理画面 (https://admin.shopify.com) にログインし、ストアの `*.myshopify.com` ドメインを確認する（詳細は本レポート下部「きらたん向け」セクション参照）
2. Keymaster に実値を登録する:
   ```bash
   ~/keymaster/set_key.sh shopify store_domain "YOUR-STORE.myshopify.com"
   ```
3. 登録結果を確認する:
   ```bash
   ~/keymaster/get_key.sh shopify store_domain
   # → PLACEHOLDER ではなく YOUR-STORE.myshopify.com が返ること
   ```
4. `start_beads_shop.sh` を再起動して反映を確認する

---

## きらたん向け: 正しい store_domain の確認手順

Keymaster に登録すべき `store_domain` の値は、Shopify 管理画面から以下の手順で確認できます。

### 手順

1. **Shopify 管理画面にログイン**
   - ブラウザで https://admin.shopify.com にアクセスし、akari-beads-shop のアカウントでログインする

2. **ストアの myshopify.com ドメインを確認する**（以下いずれかの方法）

   **方法 A: URL バーから確認**
   - ログイン後、管理画面の URL が `https://admin.shopify.com/store/xxxxxxxx/...` の形式になっている
   - この `xxxxxxxx` 部分がストア名で、store_domain は **`xxxxxxxx.myshopify.com`** となる

   **方法 B: 設定画面から確認**
   - 左下の「設定」→「ドメイン」を開く
   - 「Shopify が管理するドメイン」欄に `xxxxxxxx.myshopify.com` が表示されている
   - これが store_domain の値

3. **Keymaster に登録**
   - 確認した値（例: `akari-beads.myshopify.com`）を Keymaster の `shopify/store_domain` に設定する
   ```
   ~/keymaster/set_key.sh shopify store_domain "xxxxxxxx.myshopify.com"
   ```

4. **登録後の確認**
   ```
   ~/keymaster/get_key.sh shopify store_domain
   ```
   `PLACEHOLDER` ではなく、設定した `xxxxxxxx.myshopify.com` が返ることを確認する

### 注意
- カスタムドメイン（例: `shop.akari-beads.com`）を使用している場合でも、Shopify API が要求するのは **`*.myshopify.com`** 形式のドメインです。カスタムドメインではなく myshopify.com ドメインを登録してください。

---

## PLACEHOLDER 時の挙動分析 (2026-03-25)

Keymaster `shopify/store_domain` が `PLACEHOLDER` のままの場合、以下の挙動となる。

| レイヤー | 挙動 | 詳細 |
|---|---|---|
| `start_beads_shop.sh` | WARNING を出して **起動続行** | L28 で `PLACEHOLDER` を検出し `SHOPIFY_STORE` env にフォールバック。それも空なら `SHOPIFY_STORE_DOMAIN=""` のまま uvicorn を起動 |
| `GET /` | **200 OK** | ドメイン不要のため正常応答 |
| `GET /health` | **503** | L65: `SHOPIFY_STORE_DOMAIN` が空 → ステータス 503 を返す |
| `GET /products` | **500** | `_shopify_base_url()` (L32-33) が `HTTPException(500, "SHOPIFY_STORE_DOMAIN not configured")` を raise |
| `POST /products/create` | **500** | 同上 |

**結論: サーバーは起動するが degraded 状態。商品関連 API は全て 500 エラー。**

### きらたん向け: 最短修正手順（3コマンド）

```bash
# 1. Shopify 管理画面の URL から myshopify.com ドメインを確認済みとして:
~/keymaster/set_key.sh shopify store_domain "YOUR-STORE.myshopify.com"

# 2. 確認
~/keymaster/get_key.sh shopify store_domain
# → YOUR-STORE.myshopify.com が返ればOK

# 3. サービス再起動
sudo systemctl restart akari-beads-shop
# または: start_beads_shop.sh を再実行
```

再起動後 `curl http://localhost:8788/health` で `shopify_domain` に設定値が表示され、ステータス 200 になれば完了。

---

## 次のステップ

### Step 1: Shopify ストアを開設する

1. https://www.shopify.com にアクセスし、新規ストアを作成する
2. ストア名は `akari-beads` など、ビーズワークスショップとわかる名前にする
3. 管理画面 → 「設定」→「アプリと販売チャネル」→「アプリを開発」から **カスタムアプリ** を作成する
4. Admin API のアクセススコープで以下を許可する:
   - `write_products` / `read_products`（商品の登録・一覧取得に必要 — `server.py` の `/products/create`, `/products` が使用）
   - `write_orders` / `read_orders`（注文 webhook 受信に必要）
5. アプリをインストールし、**Admin API アクセストークン** を控える

### Step 2: Keymaster にドメインと API キーを登録する

`server.py` は Keymaster 経由で `shopify/api_key` を取得し、`start_beads_shop.sh` は `shopify/store_domain` を取得している。両方を登録する必要がある。

```bash
# store_domain を登録（現在 PLACEHOLDER が返る状態）
~/keymaster/set_key.sh shopify store_domain "YOUR-STORE.myshopify.com"

# Admin API アクセストークンを登録
~/keymaster/set_key.sh shopify api_key "shpat_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# 登録確認
~/keymaster/get_key.sh shopify store_domain   # → YOUR-STORE.myshopify.com
~/keymaster/get_key.sh shopify api_key        # → shpat_xxxx...
```

登録後、`start_beads_shop.sh` を再起動し `/health` エンドポイント（port 8788）で `shopify_domain` と `keymaster` が両方 `ok` になることを確認する。

### Step 3: Webhook を設定する

現在 `server.py` には webhook 受信エンドポイントが存在しない。以下の順で対応する。

1. **server.py に webhook エンドポイントを追加する**
   - `POST /webhooks/orders/create` — 注文作成時の通知受信用
   - Shopify の `X-Shopify-Hmac-Sha256` ヘッダーで署名検証を行うこと
   - webhook シークレットは `~/keymaster/set_key.sh shopify webhook_secret "..."` で Keymaster に登録し、`get_key("shopify", "webhook_secret")` で取得する

2. **Shopify 管理画面で webhook を登録する**
   - 管理画面 → 「設定」→「通知」→「Webhook」
   - イベント: `Order creation`
   - URL: `https://<公開ドメイン>:8788/webhooks/orders/create`
   - フォーマット: JSON

3. **公開 URL の確保**
   - Shopify webhook はインターネット経由でアクセスできる URL が必要
   - リバースプロキシ or トンネル（ngrok 等）経由で port 8788 を公開する
   - HTTPS が必須

---

## ブロッカー#4 検証ログ (2026-03-25 06:30 UTC)

### systemd unit 検証

```
# systemctl cat akari-beads-shop
WorkingDirectory=/home/kawaii_ai_office/akari-beads-shop   ← 正しい
ExecStart=/home/kawaii_ai_office/akari-beads-shop/start_beads_shop.sh  ← 正しい
User=kawaii_ai_office, Restart=always, Type=simple
```

両パスともリポジトリの実ディレクトリと一致。問題なし。

### プロセス状態

| 項目 | 旧 (レポート時点) | 現在 |
|---|---|---|
| PID | 515 | 1067583 |
| 起動日時 | 2026-03-24 17:13 | 2026-03-25 06:05 UTC |
| CWD | 未確認 | `/home/kawaii_ai_office/akari-beads-shop` (`/proc/1067583/cwd` で確認) |
| `GET /` | 404 | **200** |
| `GET /health` | `{"status":"ok"}` | **`{"service":"ok","keymaster":"ok","shopify_domain":"dandan-brothers.myshopify.com"}`** (HTTP 200) |

### 結論

**ブロッカー#4 は解消済み。** サービスは 2026-03-25 に再起動され、最新の `server.py` が配信されている。

### 補足: 残存する問題

- **Keymaster `shopify/store_domain` は依然 `PLACEHOLDER`** だが、`/health` は `dandan-brothers.myshopify.com` を表示 → `start_beads_shop.sh` の `SHOPIFY_STORE` 環境変数フォールバック経由で設定された可能性が高い
- **`GET /products` → `Invalid API key or access token`** — Shopify API キーが未登録 or 無効のため商品 API はまだ動作しない（ブロッカー#2 に該当）
