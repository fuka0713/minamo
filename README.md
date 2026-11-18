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
| 🆕 AI（Gemini / xAI Grok）で画像を解析する（鍵がなければ OCR とルール） | F-05 |
| 🆕 推薦：AI が推薦日と推薦理由を考え、1つを自動でリマインドにする（期間・締切・発売日・給料日・お店の場所から） | UC03, UC04 |
| 🆕 場所（お店・地点）と結びつけ、推薦理由に使う・近くを通ったら知らせる（お店はダミーのデータ） | UC06 |

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
API は **解析 API** と **推薦 API** に分けている。

| | 解析 API（`/api/screenshots/...`） | 推薦 API（`/api/recommendations/...`） |
|---|---|---|
| 役わり | スクショから項目を取り出す | いつ・どこで思い出させるか（通知のもと）を考える |
| AI の使い方 | 画像を読む（商品名・価格・ジャンル・お店・期間） | **推薦日と推薦理由を考える**、近くのお店での一言を考える |
| AI がないとき | OCR（Tesseract）＋ルール | ルール（下の表）＋お店の場所をそえた理由 |

1. **登録** `POST /api/screenshots`：画像を storage に保存し、「登録した日」と「画像」だけを入れる（解析の状態は pending）
2. **解析** `POST /api/screenshots/{id}/analyze`：商品名・説明文・価格・ジャンル・お店（種類・名前）・期間（開催期間・締切・発売日）を、埋められるところだけ埋める
   - サーバーの `.env` に AI の鍵（`GEMINI_API_KEY` か `XAI_API_KEY`）があれば AI で画像を解析する。失敗したら自動で OCR とルールに戻る。使った解析は `analysis.analyzer`（`gemini` / `xai` / `rules`）
   - AI を使うときも OCR は動かし、読み取った文字は検索用に残す。AI が空にしたお店の名前・期間は、OCR の文字からおぎなう
   - ユーザーが直した項目（`edited_fields`）は、再解析で上書きしない。失敗したら `failed` になり、もう一度呼べばやり直せる
3. **推薦** `POST /api/recommendations/items/{id}`：推薦日と推薦理由を最大3つ作り、1つを自動でリマインドにする
   - AI があれば、期間・締切・発売日・給料日・季節・**お店の場所**から AI が考える。なければ下の表のルール
   - 画面は解析のすぐあとにこれを呼ぶ。ホームは `GET /api/recommendations`、詳細は `GET /api/recommendations/items/{id}`
4. **場所** `PUT /api/screenshots/{id}/place` で「ここを通ったら知らせて」の地点を登録。`POST /api/recommendations/nearby` に今いる場所を送ると、近くで買えるものが理由つきで返る

### ルールで作る推薦（AI がないとき・AI へのヒント）（`app/services/timing.py`）
| 解析で分かったこと | いつ知らせるか | 例の理由 |
|---|---|---|
| 開催期間の終わり | 終わる3日前の 20:00 | 「期間が終わる3日前です。行くか・買うかを決めるのにちょうどいい日です。」 |
| 開催期間の始まり | 始まる日の 10:00 | 「始まる日です。」 |
| 締切 | 締切の前日 20:00 | 「締切の前日です。申し込むなら今のうちです。」 |
| 発売日 | 発売日の 10:00 | 「発売日です。」 |
| ジャンルが飲食店 | 次の土曜 11:00 | 「週末です。行けるか考えてみませんか？」 |
| （いつでも） | 次の給料日 20:00（仮で毎月25日。土日なら直前の金曜） | 「給料日です。買うか決めませんか？ IKEA 新宿（新宿）で買えます。」 |
| どれもない | 1週間後 20:00 | 「1週間たちました。今も欲しいですか？」 |

- 過去の日時は使わない。同じ日に2つは入れない。自動でリマインドにするのは、締切 → 期間の終わり → 発売日 → 始まる日 の順に見つかったもの（なければ一番早いもの）
- ユーザーが選んだリマインド（`POST /api/recommendations/{id}/accept` など）があるときは、推薦を作り直しても自動のリマインドは入れない

### 生成 AI の設定（`app/services/llm.py`・`app/services/ai.py`）
| 設定（サーバーの `/opt/minamo/.env`） | 説明 |
|---|---|
| `LLM_PROVIDER` | 使う AI：`gemini`（既定）/ `xai`。選んだ方の鍵が無ければ、もう一方の鍵を使う |
| `GEMINI_API_KEY` | Google AI Studio（https://aistudio.google.com/apikey）で発行。無料枠あり |
| `GEMINI_ENDPOINT` | ふつうは空でよい。空なら Gemini API（AI Studio の鍵。`AIza…` も新しい形の `AQ.…` もある）を先に試し、鍵を受けつけなければ Vertex AI も試す。`gemini` / `vertex` で決め打ちもできる |
| `XAI_API_KEY` | xAI Console（https://console.x.ai）で発行。クレジットを先に買う（有料） |
| `GEMINI_MODEL` / `XAI_MODEL` | 使うモデル（既定 `gemini-2.5-flash` / `grok-4`）。使える名前は各サービスの画面で確認する（xAI は画像を読めるモデルにする） |

- 鍵はサーバーの `.env` だけに書く（GitHub・画面には出さない）。鍵は URL ではなくヘッダーで送る
- AI の答えは形を確かめてから使う（過去の日・同じ日・決まり以外の値は捨てる）。全部だめならルールに戻る
- ⚠ AI を使うと、スクショや欲しいものの情報が Google / xAI に送られる。無料枠では送った内容がサービス改善に使われることがある

### 場所のしくみ（`app/services/places.py`）
- お店の情報は `POI_PROVIDER` で決まる：**`dummy`（既定）＝新宿・渋谷・池袋あたりの仮のお店（`DUMMY_STORES`）**／`overpass`＝OpenStreetMap で調べる（キー不要・位置は約100mに丸めて送る）／`none`
- 推薦：欲しいものを買えそうなお店（名前かジャンルの種類が合うもの）の、いちばん近いものを推薦理由に使う（現在地がなければ新宿駅から探す）
- 近く：登録した地点の半径（既定 200m）か、合うお店が 300m 以内にあれば知らせる。同じ商品は24時間に1回まで。「いらない」は知らせない。送られた現在地は保存しない
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
| POST | `/api/screenshots/{id}/analyze` | （FastAPI・解析）解析して項目を埋める（`?force=true` で直した項目も上書き） |
| POST | `/api/screenshots/{id}/reminders` | 🆕（FastAPI・解析）自分で決めた日時でリマインドを入れる（`remindAt` `reason`） |
| PUT | `/api/screenshots/{id}/place` | 🆕（FastAPI・解析）場所を登録（`name` `category` `lat` `lng` `radiusM` `visible`） |
| POST | `/api/recommendations/items/{id}` | 🆕（FastAPI・推薦）推薦日と推薦理由を作る（body に `lat` `lng` を入れると近いお店を使う） |
| GET | `/api/recommendations/items/{id}` | 🆕（FastAPI・推薦）欲しいもの1件の推薦 |
| GET | `/api/recommendations?limit=4` | 🆕（FastAPI・推薦）ホーム用：見直すとよい欲しいもの |
| POST | `/api/recommendations/{id}/accept` | 🆕（FastAPI・推薦）推薦をリマインドにする |
| POST | `/api/recommendations/nearby` | 🆕（FastAPI・推薦）今いる場所（`lat` `lng`）の近くで買える欲しいもの |
| POST | `/api/items` | （Express・旧）スクショを登録して、その場で解析もする |
| GET | `/api/items/:id` | 1件の詳細 |
| GET | `/api/items/:id/image` | 画像 |
| PATCH | `/api/items/:id` | 修正（`title` `price` `memo` `genre` `period`） |
| DELETE | `/api/items/:id` | 削除 |

ログイン（クッキー）は、`/api/auth/signup`・`login`・`logout` と `/api/genres` 以外のすべてで必要。自分のデータだけが返る。

## ジャンル分けの精度を上げるには
`backend/src/genres.ts` のキーワードを足す。今は AI を使わず、キーワードの数で決めている。
