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
   - 価格と場所は、間違っているとストレスなので、最初は画面に出さない（`price_visible` / `place_visible`）
   - ユーザーが直した項目（`edited_fields`）は、再解析で上書きしない
   - 失敗したら `failed` になり、もう一度呼べばやり直せる
3. 画面は、登録したらすぐ一覧に「解析中…」を出し、続けて解析を呼ぶ

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
| POST | `/api/screenshots/{id}/analyze` | （FastAPI）解析して項目を埋める（`?force=true` で直した項目も上書き） |
| POST | `/api/items` | （Express・旧）スクショを登録して、その場で解析もする |
| GET | `/api/items/:id` | 1件の詳細 |
| GET | `/api/items/:id/image` | 画像 |
| PATCH | `/api/items/:id` | 修正（`title` `price` `memo` `genre` `period`） |
| DELETE | `/api/items/:id` | 削除 |

ログイン（クッキー）は、`/api/auth/signup`・`login`・`logout` と `/api/genres` 以外のすべてで必要。自分のデータだけが返る。

## ジャンル分けの精度を上げるには
`backend/src/genres.ts` のキーワードを足す。今は AI を使わず、キーワードの数で決めている。
