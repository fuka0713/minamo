# minamo（試作版）

> 🧪 この README は、main に入れた変更がサーバーに自動で反映されるかどうかのテストも兼ねています。
> 🚧 API や機能の中身はまだ検討中です。ここにあるのは動作確認のための仮のものです。

スクショから「欲しいものリスト」を作るアプリの試作版です。
要件定義の **土台の部分だけ** を作っています。中核の「思い出させる」機能（通知・給料日リマインド・コラボグッズ推薦）は、まだ入れていません。

## できること
| 機能 | 要件の番号 |
|---|---|
| アカウント登録・ログイン・ログアウト（スクショはアカウントごとに分かれる） | UC01, UC02 |
| スクショをアップロードして登録する（複数枚 OK） | F-01, F-02 |
| 画像から文字を読み取る（OCR、日本語・英語） | F-05 |
| 商品名・価格・URL を自動で取り出す | F-05 |
| コラボなどの期間（開催期間・締切・発売日）を自動で読み取り、直せる | UC19 |
| ジャンルを自動で分ける | F-06, UC12 |
| ジャンルが違うときにユーザーが直す | F-09, UC13 |
| 一覧・ジャンルで絞り込み・キーワード検索 | F-20, F-22 |
| 詳細・修正・削除 | F-21, F-32 |
| 🆕 解析の結果から、リマインドするタイミングを推測する（期間・締切・発売日・給料日など。理由つき） | UC03, UC04 |
| 🆕 場所（お店・地点）と結びつけ、その近くを通ったら知らせる | UC06 |

## フォルダの構成
```
minamo/
├── compose.yaml          … 4つのサービスをまとめて起動する設定
├── .env.example          … パスワードの見本（本物は .env に書く。GitHub には上げない）
├── .github/workflows/
│   └── pipeline.yml      … CI/CD（チェック → main に入ったらサーバーに反映）
├── frontend/             … 画面（Next.js）
│   ├── app/login/page.tsx        … ログイン・アカウント登録
│   ├── app/page.tsx              … トップ：アップロードと一覧
│   ├── app/items/[id]/           … 詳細：ジャンルの修正・編集・削除
│   ├── lib/api.ts                … バックエンドを呼ぶ関数
│   └── next.config.ts            … /api/... をバックエンドに中継する設定
├── backend-py/           … API（FastAPI）：スクショの登録と解析
│   ├── app/main.py               … 入口（routers をつなぐ）。説明ページは /api/docs
│   ├── app/models/               … データベースのテーブル（SQLAlchemy）
│   ├── app/schemas/              … API の入出力の形（Pydantic）
│   ├── app/crud/                 … データベースの読み書き
│   ├── app/routers/              … API の URL ごとの処理（screenshots.py）
│   ├── app/services/             … OCR・画像の保存・解析のルール
│   └── tests/                    … テスト（python -m pytest）
└── backend/              … API（Express）：アカウント・一覧・詳細・修正・削除
    ├── src/index.ts              … API の入口（ここを読めば全体が分かる）
    ├── src/auth.ts               … アカウント登録・ログイン・ログアウト
    ├── src/analyze.ts            … 文字から商品名・価格・ジャンル・期間を取り出す
    ├── src/analyze.test.ts       … analyze.ts のテスト
    ├── src/genres.ts             … ジャンルとキーワードの一覧
    ├── src/ocr.ts                … 文字認識（Tesseract を呼ぶ）
    ├── src/db.ts                 … データベース（テーブルは起動時に自動で作る）
    └── src/storage.ts            … 画像の保存（SeaweedFS）
```

## しくみ
```
ブラウザ ──▶ frontend（画面）──/api/screenshots…──▶ backend-py（FastAPI）──┬──▶ db（PostgreSQL）
                              └─/api/…（それ以外）─▶ backend（Express）──────┴──▶ storage（SeaweedFS：画像）
```
- ブラウザがつながるのは frontend だけ。`/api/...` は frontend がそのまま backend に中継する
- backend・db・storage はサーバーの外に公開しない

## スクショを登録したときの流れ（backend-py）
1. **登録** `POST /api/screenshots`：画像を storage に保存し、「登録した日」と「画像」だけを入れる（解析の状態は pending）
2. **解析** `POST /api/screenshots/{id}/analyze`：Tesseract で文字を読み取り、商品名・説明文・価格・ジャンル・場所（お店の種類）を、埋められるところだけ埋める
   - 🆕 サーバーの `.env` に `GEMINI_API_KEY` があれば **Gemini で画像を解析**する（失敗したら自動で OCR とルールに戻る）。使った解析は `analysis.analyzer`（`gemini` / `rules`）で分かる
   - Gemini を使うときも OCR は動かし、読み取った文字は検索用に残す。Gemini が空にしたお店の名前・期間は、OCR の文字からおぎなう
   - 価格と場所は、間違っているとストレスなので、最初は画面に出さない（`price_visible` / `place_visible`）
   - ユーザーが直した項目（`edited_fields`）は、再解析で上書きしない
   - 失敗したら `failed` になり、もう一度呼べばやり直せる
3. 画面は、登録したらすぐ一覧に「解析中…」を出し、続けて解析を呼ぶ
4. 🆕 **いつ思い出すか**：解析で読み取った期間から、リマインドを1つ自動で入れる（下の表）。`GET /api/screenshots/{id}/reminder-suggestions` で候補（最大3つ・理由つき）を見て、`POST /api/screenshots/{id}/reminders` で選び直せる
5. 🆕 **どこで思い出すか**：`PUT /api/screenshots/{id}/place` で場所（お店の名前・緯度経度・半径）を登録。画面が `POST /api/screenshots/nearby` に今いる場所を送ると、近くにあるものが返る

### リマインドのタイミングの決め方（`app/services/timing.py`）
| 解析で分かったこと | いつ知らせるか | 例の理由 |
|---|---|---|
| 開催期間の終わり | 終わる3日前の 20:00 | 「期間が終わる3日前です。行くか・買うかを決めるのにちょうどいい日です。」 |
| 開催期間の始まり | 始まる日の 10:00 | 「始まる日です。」 |
| 締切 | 締切の前日 20:00 | 「締切の前日です。申し込むなら今のうちです。」 |
| 発売日 | 発売日の 10:00 | 「発売日です。」 |
| ジャンルが飲食店 | 次の土曜 11:00 | 「週末です。行けるか考えてみませんか？」 |
| （いつでも） | 次の給料日 20:00（仮で毎月25日。土日なら直前の金曜） | 「給料日です。買うか決めませんか？」 |
| どれもない | 1週間後 20:00 | 「1週間たちました。今も欲しいですか？」 |

- 過去の日時は使わない。同じ日に2つは入れない。自動で入れるのは「期間から作った候補の一番早いもの」（なければ一番早いもの）
- ユーザーが自分で選んだリマインドがあるときは、再解析しても自動のリマインドは入れない

### Gemini の設定（`app/services/gemini.py`）
| 設定（サーバーの `/opt/minamo/.env`） | 説明 |
|---|---|
| `GEMINI_API_KEY` | Google AI Studio（https://aistudio.google.com/apikey）で発行した鍵。空なら Gemini を使わない |
| `GEMINI_MODEL` | 使うモデル（既定 `gemini-2.5-flash`）。使えるモデル名は AI Studio で確認する |

- 鍵はサーバーの `.env` だけに書く（GitHub・画面には出さない）。鍵は URL ではなくヘッダーで送る
- ⚠ Gemini を使うと、スクショが Google に送られる。無料枠では、送った内容が Google のサービス改善に使われることがある

### 場所で知らせるしくみ（`app/services/places.py`）
1. **登録した地点の近く**：商品に緯度・経度を登録してあれば、その半径（既定 200m）に入ったら知らせる。外部には問い合わせない
2. **同じお店が近くにある**：お店の名前（解析で「IKEA」「マツキヨ」などを読み取る）か、ジャンルのお店の種類（コスメ→ドラッグストア など）だけのときは、
   OpenStreetMap の Overpass API で、半径 300m 以内にそのお店があるか調べる。**`POI_PROVIDER=overpass` のときだけ**（キーは不要）。送る位置は約100mに丸める
- 同じ商品を場所で知らせるのは24時間に1回まで。「いらない」にしたものは知らせない。送られた現在地は保存しない
- ⚠ ブラウザでは、**画面を開いている間しか**現在地を送れない（閉じているときに「通ったら知らせる」には、スマホアプリのジオフェンスが必要）

## 手元で動かす（Docker）
```bash
cp .env.example .env
docker compose up -d --build
```
ブラウザで http://localhost を開く。止めるときは `docker compose down`。

## チェック（push する前に）
```bash
cd frontend && npm ci && npm run lint && npm run build && cd ..
cd backend && npm ci && npm run lint && npm test && npm run build && cd ..
cd backend-py && pip install -r requirements.txt && ruff check . && python -m pytest -q && cd ..
```

## API の一覧（backend）
| メソッド | URL | 内容 |
|---|---|---|
| POST | `/api/auth/signup` | アカウント登録（`email` `password`）→ ログインした状態になる |
| POST | `/api/auth/login` | ログイン |
| POST | `/api/auth/logout` | ログアウト |
| GET | `/api/auth/me` | ログインしている人 |
| GET | `/api/genres` | ジャンルの一覧 |
| GET | `/api/items?genre=cosme&q=リップ` | 一覧（絞り込み・検索） |
| POST | `/api/screenshots` | （FastAPI）スクショを登録（フォームの `files` に画像）。登録した日と画像だけ入る |
| POST | `/api/screenshots/{id}/analyze` | （FastAPI）解析して項目を埋める（`?force=true` で直した項目も上書き）。リマインドも1つ自動で入れる |
| GET | `/api/screenshots/{id}/reminder-suggestions` | 🆕（FastAPI）リマインドの候補（最大3つ・理由つき） |
| POST | `/api/screenshots/{id}/reminders` | 🆕（FastAPI）リマインドを入れる（`remindAt` `reason`） |
| PUT | `/api/screenshots/{id}/place` | 🆕（FastAPI）場所を登録（`name` `category` `lat` `lng` `radiusM` `visible`） |
| POST | `/api/screenshots/nearby` | 🆕（FastAPI）今いる場所（`lat` `lng`）の近くにある欲しいもの |
| POST | `/api/items` | （Express・旧）スクショを登録して、その場で解析もする |
| GET | `/api/items/:id` | 1件の詳細 |
| GET | `/api/items/:id/image` | 画像 |
| PATCH | `/api/items/:id` | 修正（`title` `price` `memo` `genre` `period`） |
| DELETE | `/api/items/:id` | 削除 |

ログイン（クッキー）は、`/api/auth/signup`・`login`・`logout` と `/api/genres` 以外のすべてで必要。自分のデータだけが返る。

## ジャンル分けの精度を上げるには
`backend/src/genres.ts` のキーワードを足す。今は AI を使わず、キーワードの数で決めている。
