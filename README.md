# Threads × 楽天アフィリエイト 自動bot

1日9回（7時〜23時の2時間おき）、Threadsに自動で投稿して楽天アフィリエイトの売上につなげるbotです。
**費用は0円**（Threads API・Gemini無料枠・楽天API・GitHub Actions はすべて無料）。PCの電源も不要です。

## 稼ぐ仕組み
- **商品紹介（6割）**：本投稿で季節や生活の悩みから入り、**リプ欄に楽天リンク**を置く（Threadsでよく使われる形）
- **共感・お役立ち（4割）**：リンクなしの投稿でフォロワーを増やす（宣伝ばかりだと見られなくなるため）
- 商品は楽天APIで **レビュー30件以上・評価4.0以上** のものから自動で選びます（30日間は同じ商品を紹介しません）
- **今の季節に合うジャンルを優先**：11〜12月はふるさと納税（北海道の海産物・米など）、お歳暮、除雪・防寒グッズが中心
- 反応の良かったジャンルが自動で選ばれやすくなります（2割は別ジャンルで新しい当たりを探します）
- 商品紹介には自動で【PR】を付けます（ステマ規制への対応）

---

## セットアップ（初回だけ・30分ほど）

### 1. Threadsのアカウント
Instagramの **rakuten.aff** でThreadsにログインして、プロフィールを作ります。
プロフィール文の例：「北海道の居酒屋店主｜冬は除雪｜楽天で評判のいいものを紹介｜※PRを含みます」

### 2. ThreadsのAPIトークン（いちばん大変なところ）
1. https://developers.facebook.com でアプリを作成 → ユースケースで **「Threads APIにアクセス」** を選ぶ
2. ユースケースの設定で、次の権限を追加：`threads_basic` `threads_content_publish` `threads_manage_insights`
3. 「役割」→ **Threadsテスター** に自分のThreadsアカウントを追加
4. Threadsアプリ → 設定 → アカウント → **ウェブサイトのアクセス許可** → 招待を承認
5. ユースケース設定の **ユーザートークン生成ツール** でトークンを発行（60日有効の長期トークン）
6. 同じ画面に出る **ThreadsユーザーID** もメモ

※自分のアカウントに投稿するだけなら、Metaの審査（App Review）は不要です。
※画面の名前は変わることがあります。迷ったらその画面のスクショを送ってください。

### 3. 楽天のキー
https://webservice.rakuten.co.jp でアプリ登録 → **アプリID** と **アクセスキー** をメモ。
登録時に入れた「WebサイトURL」も、あとで**まったく同じ文字**で使います。

### 4. GitHubに置く
1. GitHubで **Public** のリポジトリを作成（Actionsが無料で無制限。キーはSecretsなので外から見えません）
2. このフォルダの中身を丸ごとアップロード（`.github` フォルダも忘れずに）
3. Settings → Secrets and variables → Actions に登録：

| 名前 | 中身 | 種類 |
|---|---|---|
| `THREADS_ACCESS_TOKEN` | 手順2のトークン | Secrets |
| `THREADS_USER_ID` | 手順2のユーザーID | Secrets |
| `GEMINI_API_KEY` | X botと同じもの | Secrets |
| `RAKUTEN_APP_ID` / `RAKUTEN_ACCESS_KEY` | 手順3 | Secrets |
| `GH_PAT` | トークン自動延長用（下記） | Secrets |
| `RAKUTEN_REFERER` | 楽天に登録したWebサイトURL | Variables |

**GH_PAT の作り方**（トークンが60日で切れるのを防ぐため）：
GitHub右上の自分のアイコン → Settings → Developer settings → Fine-grained tokens → Generate new token
→ このリポジトリだけを選び、Permissions の **Secrets** を「Read and write」にして発行。
これで毎週月曜にトークンが自動で延長されます。

### 5. テスト → 本番
1. Actions →「Threads楽天bot」→ Run workflow（テスト実行に✅、種類は product）
2. ログに本投稿とリプ欄の文が出ればOK
3. ✅を外してもう一度実行 → 実際に投稿されます。Threadsで見た目を確認
4. あとは自動で1日9回動きます

## 確認するところ
- `data/report.md`：ジャンル別の反応
- 売上：楽天アフィリエイトの管理画面

## 調整（`src/config.py` か Variables）
| 項目 | 意味 | 初期値 |
|---|---|---|
| `PRODUCT_RATIO` | 商品紹介の割合 | 0.6 |
| `QUIET_HOURS` | 投稿しない時間 | 0〜6時 |
| `PERSONA` | 投稿する人のキャラ（事実だけ） | 北海道の居酒屋店主・除雪 |
| `GENRES` | 紹介ジャンルと楽天の検索語・季節 | 8ジャンル |

## 注意
- 投稿文はAIが作ります。体験談の作り話・誇大表現・ポイント倍率などの変わりやすい情報は書かないよう指示していますが、最初の数日はThreadsで中身を確認してください
- 価格は投稿時点のものです（リプ欄に日付を入れています）
- Threadsの仕様が変わって動かなくなることがあります。Actionsのログにエラーが出たら、そのまま貼って相談してください
