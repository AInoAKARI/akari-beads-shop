# TODO: きらたん — Shopify ストア開設後の最小手順

> Shopify ストアを開設し、`*.myshopify.com` ドメインとAdmin APIトークンが手元にある前提です。
> 詳細な補足は [SETUP_TODO.md](SETUP_TODO.md) を参照してください。

---

## 1. store_domain を Keymaster に登録

```bash
~/keymaster/set_key.sh shopify store_domain "YOUR-STORE.myshopify.com"
```

確認:
```bash
~/keymaster/get_key.sh shopify store_domain
# → YOUR-STORE.myshopify.com が返ること（PLACEHOLDER でないこと）
```

## 2. api_key を Keymaster に登録

```bash
~/keymaster/set_key.sh shopify api_key "shpat_ここにトークンを貼る"
```

確認:
```bash
~/keymaster/get_key.sh shopify api_key
# → shpat_... が返ること（PLACEHOLDER でないこと）
```

## 3. サービスを起動

> **注意**: `sudo systemctl restart akari-beads-shop` では Keymaster 取得ロジックを通らないため、
> store_domain が反映されません。必ず以下の手順で起動してください。

```bash
sudo systemctl stop akari-beads-shop
~/akari-beads-shop/start_beads_shop.sh
```

## 4. ヘルスチェック

```bash
curl -s http://localhost:8788/health | python3 -m json.tool
```

**OK の条件（全て満たすこと）:**

- [ ] HTTP ステータスが **200**（503 でない）
- [ ] `shopify_domain` に正しいドメインが表示されている
- [ ] `keymaster` が `ok`

503 が返る場合 → Step 1-2 の登録値を確認し、Step 3 からやり直してください。

---

**完了後:** `curl http://localhost:8788/products` が正常応答すれば、商品登録 API も使えます。

---

## 0. Shopify ストア開設（まだの場合）

- https://www.shopify.com で新規ストアを作成（ストア名例: `akari-beads`）
- 管理画面 →「設定」→「アプリと販売チャネル」→「アプリを開発」でカスタムアプリを作成し、`write_products` / `read_products` / `write_orders` / `read_orders` スコープを許可
- アプリをインストールし Admin API アクセストークン (`shpat_...`) を控える
- 管理画面 URL の `admin.shopify.com/store/xxxxxxxx` から `xxxxxxxx.myshopify.com` を確認し、上記 Step 1〜4 を実施
- 最終確認: `curl http://localhost:8788/products` が 200 を返し、`/health` の `shopify_domain` が正しい値であれば完了
