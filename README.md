# minamo（試作版）

> 🧪 この README は、main に入れた変更がサーバーに自動で反映されるかどうかのテストも兼ねています。

スクショから「欲しいものリスト」を作るアプリの試作版です。
要件定義の **土台の部分だけ** を作っています。中核の「思い出させる」機能（通知・給料日リマインド・コラボグッズ推薦）は、まだ入れていません。

## できること
| 機能 | 要件の番号 |
|---|---|
| スクショをアップロードして登録する（複数枚 OK） | F-01, F-02 |
| 画像から文字を読み取る（OCR、日本語・英語） | F-05 |
| 商品名・価格・URL を自動で取り出す | F-05 |
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
│   ├── app/page.tsx              … トップ：アップロードと一覧
│   ├── app/items/[id]/           … 詳細：ジャンルの修正・編集・削除
│   ├── lib/api.ts                … バックエンドを呼ぶ関数
│   └── next.config.ts            … /api/... をバックエンドに中継する設定
└── backend/              … API（Express）
    ├── src/index.ts              … API の入口（ここを読めば全体が分かる）
    ├── src/analyze.ts            … 文字から商品名・価格・ジャンルを取り出す
    ├── src/analyze.test.ts       … analyze.ts のテスト
    ├── src/genres.ts             … ジャンルとキーワードの一覧
    ├── src/ocr.ts                … 文字認識（Tesseract を呼ぶ）
    ├── src/db.ts                 … データベース（テーブルは起動時に自動で作る）
    └── src/storage.ts            … 画像の保存（SeaweedFS）
```

## しくみ
```
ブラウザ ──▶ frontend（画面）──/api/...──▶ backend（API）──▶ db（PostgreSQL）
                                                        └──▶ storage（SeaweedFS：画像）
```
- ブラウザがつながるのは frontend だけ。`/api/...` は frontend がそのまま backend に中継する
- backend・db・storage はサーバーの外に公開しない

## スクショを登録したときの流れ（backend/src/index.ts）
1. 画像を storage に保存
2. Tesseract で文字を読み取る
3. 読み取った文字から、商品名・価格・URL・ジャンルを取り出す（`analyze.ts`）
4. データベースに保存

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
```

## API の一覧（backend）
| メソッド | URL | 内容 |
|---|---|---|
| GET | `/api/genres` | ジャンルの一覧 |
| GET | `/api/items?genre=cosme&q=リップ` | 一覧（絞り込み・検索） |
| POST | `/api/items` | スクショを登録（フォームの `files` に画像） |
| GET | `/api/items/:id` | 1件の詳細 |
| GET | `/api/items/:id/image` | 画像 |
| PATCH | `/api/items/:id` | 修正（`title` `price` `memo` `genre`） |
| DELETE | `/api/items/:id` | 削除 |

## ジャンル分けの精度を上げるには
`backend/src/genres.ts` のキーワードを足す。今は AI を使わず、キーワードの数で決めている。
