// PostgreSQL（データベース）への接続
import pg from "pg";

export const db = new pg.Pool({ connectionString: process.env.DATABASE_URL });

// 起動したときに、テーブルがなければ作る（列が足りなければ足す）
export async function createTables() {
  // ユーザー（アカウント）
  await db.query(`
    CREATE TABLE IF NOT EXISTS users (
      id            SERIAL PRIMARY KEY,
      email         TEXT NOT NULL UNIQUE,
      password_hash TEXT NOT NULL,              -- パスワードそのものは保存しない
      created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
    )
  `);

  // ログイン中の印（ブラウザのクッキーに入れる合言葉）
  await db.query(`
    CREATE TABLE IF NOT EXISTS sessions (
      token      TEXT PRIMARY KEY,
      user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
  `);

  // 欲しいもの
  await db.query(`
    CREATE TABLE IF NOT EXISTS items (
      id           SERIAL PRIMARY KEY,
      title        TEXT    NOT NULL,                 -- 商品名
      genre        TEXT    NOT NULL,                 -- ジャンル
      genre_source TEXT    NOT NULL DEFAULT 'auto',  -- auto=自動で分類 / user=ユーザーが修正
      price        INTEGER,                          -- 価格
      url          TEXT,
      ocr_text     TEXT    NOT NULL DEFAULT '',      -- 読み取った文字
      memo         TEXT    NOT NULL DEFAULT '',
      image_key    TEXT    NOT NULL,                 -- ストレージでの画像の名前
      created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
    )
  `);
  // あとから足した列（すでにテーブルがあるサーバーでも動くように、なければ足す）
  await db.query(`
    ALTER TABLE items
      ADD COLUMN IF NOT EXISTS user_id      INTEGER REFERENCES users(id) ON DELETE CASCADE, -- 持ち主
      ADD COLUMN IF NOT EXISTS period_start DATE,  -- 開催・販売が始まる日
      ADD COLUMN IF NOT EXISTS period_end   DATE,  -- 終わる日
      ADD COLUMN IF NOT EXISTS deadline     DATE,  -- 受注・予約の締切
      ADD COLUMN IF NOT EXISTS release_date DATE,  -- 発売日
      ADD COLUMN IF NOT EXISTS period_source TEXT NOT NULL DEFAULT 'auto' -- auto=自動で読み取り / user=ユーザーが修正
  `);
}

// 日付を「YYYY-MM-DD」の文字にする（日付がなければ null）
function day(value: Date | null): string | null {
  if (!value) return null;
  const y = value.getFullYear();
  const m = String(value.getMonth() + 1).padStart(2, "0");
  const d = String(value.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

// データベースの1行を、画面に返す形に変える
export function toItem(row: any) {
  return {
    id: row.id,
    title: row.title,
    genre: row.genre,
    genreSource: row.genre_source,
    price: row.price,
    url: row.url,
    ocrText: row.ocr_text,
    memo: row.memo,
    description: row.description ?? null,
    wishStatus: row.wish_status ?? "want",
    priceVisible: row.price_visible ?? false,
    analysisStatus: row.analysis_status ?? "done",
    period: {
      start: day(row.period_start),
      end: day(row.period_end),
      deadline: day(row.deadline),
      release: day(row.release_date),
      source: row.period_source,
    },
    imageUrl: `/api/items/${row.id}/image`,
  };
}
