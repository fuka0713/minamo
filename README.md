# minamo（すくしょっぷ）

スクショした「欲しい」を忘れないためのアプリ。スクショを送ると、サーバーが文字を読み取って（OCR、または Gemini）欲しいものとして登録し、
ちょうどいいタイミングで思い出させる。

> 🧪 デモ版：ログイン画面でメールアドレスとパスワードを**空のまま**進むと、ゲストとして入れる（そのブラウザだけで使える）。
> みんなで同じデータを見たいときは、**ユーザー名 `test` ／ パスワード `test`** で入る。
> 自分のアカウントは「新規登録」で、**ユーザー名とパスワード（4文字以上）だけ**で作れる（DB の users に保存）。ログアウトは設定画面のいちばん上。

## フォルダの構成
```
minamo/
├── compose.yaml        … 4つのサービスをまとめて起動（frontend・backend-py・db・storage）
├── .env.example        … 設定の見本（本物は .env に書く。GitHub には上げない）
├── .github/workflows/
│   └── pipeline.yml    … CI/CD（チェック → main に入ったらサーバーに反映）
├── frontend/           … 画面（React + Vite。zip「sukushop-v2-updated_7」）。nginx が配り、/api を backend-py へ中継
│   └── src/services/api.ts … API とのやりとりはここに集めている
├── backend-py/         … API（FastAPI）。説明ページ（Swagger）は /api/docs
│   ├── app/models/     … テーブル（SQLAlchemy）
│   ├── app/schemas/    … API の入出力の形（Pydantic）
│   ├── app/crud/       … データベースの読み書き
│   ├── app/routers/    … URL ごとの処理
│   ├── app/services/   … 解析（OCR・ルール・Gemini）、リマインド候補、画像の保存
│   └── tests/          … テスト（python -m pytest）
├── デモ版_サイト/      … ホーム画面の HTML のデモ（参考）
└── docs/               … 要件定義
```
くわしい設計は 3Diary リポジトリの `docs/design.md` 5章、テーブルは `sukushop/docs/schema.md`。

## しくみ
```
ブラウザ ──▶ frontend（nginx）──/api/...──▶ backend-py（FastAPI）──┬──▶ db（PostgreSQL）
                                                                   ├──▶ storage（SeaweedFS：画像）
                                                                   └──▶ Gemini（GEMINI_API_KEY があるときだけ）
```

## 設定（サーバーの `/opt/minamo/.env`）
| 名前 | 必須？ | 説明 |
|---|---|---|
| `DB_USER` / `DB_PASSWORD` / `DB_NAME` | 必須 | 自分で決める |
| `S3_ACCESS_KEY` / `S3_SECRET_KEY` | 必須 | 自分で決める |
| `GEMINI_API_KEY` | 任意 | Google AI Studio で発行。空なら OCR とルールで解析 |
| `ALLOW_GUEST` | 任意（既定 true） | デモ：メールアドレスなしで入れる。閉じるときは false |

`.env` を書きかえたら、サーバーで `cd /opt/minamo` → `sudo docker compose up -d` で反映する。

## 手元で動かす（Docker）
```bash
cp .env.example .env
```

```bash
docker compose up -d --build
```
ブラウザで http://localhost を開く。止めるときは `docker compose down`。

## チェック（push する前に）
```bash
cd frontend && npm ci && npm run build && cd ..
```

```bash
cd backend-py && pip install -r requirements.txt && ruff check . && python -m pytest -q && cd ..
```

## 前の試作版から変わったこと
- 画面を Next.js の試作から、zip「sukushop-v2-updated_7」（React + Vite）に変えた
- API を FastAPI（backend-py）にまとめた。Express の backend はなくした
- データベースは新しい置き場所（ボリューム `db-data-v2`）を使う。前の試作版のデータは `db-data` に残っている
