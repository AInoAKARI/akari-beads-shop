# あかりビーズショップ セットアップガイド

おつかれさま！このガイドの手順を上から順にやれば、ビーズショップが動くようになるよ。

---

## やること一覧

1. Shopify でお店をつくる
2. アプリをつくって「合言葉（APIトークン）」をもらう
3. お店のアドレスを調べる
4. 合言葉とアドレスをサーバーに教える
5. サーバーを再起動して動作確認

---

## 1. Shopify でお店をつくる

1. https://www.shopify.com をブラウザで開く
2. 「無料体験をはじめる」からアカウントを作成
3. ストア名は **akari-beads** など、ビーズショップとわかる名前にしてね

## 2. アプリをつくって合言葉をもらう

Shopify の管理画面（ログイン後の画面）で操作するよ。

1. 左下の **「設定」** をクリック
2. **「アプリと販売チャネル」** → **「アプリを開発」** を選ぶ
3. **「カスタムアプリを作成」** ボタンを押す
4. アプリ名は何でもOK（例: `akari-api`）
5. 「Admin API のアクセススコープを設定する」で以下の4つにチェックを入れる:
   - `write_products`
   - `read_products`
   - `write_orders`
   - `read_orders`
6. 保存したら **「アプリをインストール」** を押す
7. 表示される **Admin API アクセストークン**（`shpat_` で始まる長い文字列）をコピーしてメモ帳に貼っておく

> **注意:** このトークンは一度しか表示されないので、必ずこのタイミングでコピーしてね！

## 3. お店のアドレス（ドメイン）を調べる

管理画面のURLバーを見てみて。こんな形になってるはず:

```
https://admin.shopify.com/store/xxxxxxxx/...
```

この **xxxxxxxx** の部分がお店の名前で、アドレスは **`xxxxxxxx.myshopify.com`** になるよ。

もう一つの調べ方: 「設定」→「ドメイン」→「Shopify が管理するドメイン」欄にも書いてある。

> 独自ドメイン（`shop.akari-beads.com` みたいなの）を持っていても、ここでは **必ず `○○.myshopify.com` のほう** を使ってね。

## 4. 合言葉とアドレスをサーバーに教える

ターミナルを開いて、以下のコマンドを順番に実行してね。
`xxxxxxxx` と `shpat_ここにトークンを貼る` はさっき調べた自分の値に置き換えてね。

```bash
# お店のアドレスを登録
~/keymaster/set_key.sh shopify store_domain "xxxxxxxx.myshopify.com"

# APIトークン（合言葉）を登録
~/keymaster/set_key.sh shopify api_key "shpat_ここにトークンを貼る"
```

ちゃんと登録できたか確認:

```bash
~/keymaster/get_key.sh shopify store_domain
# → xxxxxxxx.myshopify.com が表示されればOK（PLACEHOLDER と出たらやり直し）

~/keymaster/get_key.sh shopify api_key
# → shpat_... が表示されればOK
```

## 5. サーバーを再起動して動作確認

```bash
# サーバーを止める
sudo systemctl stop akari-beads-shop

# 起動スクリプトで立ち上げ直す
~/akari-beads-shop/start_beads_shop.sh
```

> `sudo systemctl restart` ではなく、**止めてからスクリプトで起動** するのがポイント！
> （スクリプト経由じゃないと、さっき登録した値が読み込まれないため）

最後に、ちゃんと動いているか確認:

```bash
curl -s http://localhost:8788/health | python3 -m json.tool
```

**成功の目印:**
- `200` が返ってくる（`503` じゃない）
- `shopify_domain` に自分のアドレスが表示されている
- `keymaster` が `ok` になっている

---

## うまくいかないときは

| 症状 | 原因と対処 |
|------|-----------|
| `/health` が 503 のまま | Step 4 の登録値が間違っている可能性あり。`get_key.sh` で値を再確認して、もう一度 Step 5 をやり直してね |
| `/products` が 500 エラー | `api_key` が未登録または間違い。Step 4 の APIトークン登録を確認してね |
| ポート番号がわからない | **8788** だよ（Notion に書いてある 8787 は古い情報なので注意） |
