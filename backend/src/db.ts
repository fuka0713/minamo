// PostgreSQL（データベース）への接続
import pg from "pg";

export const db = new pg.Pool({ connectionString: process.env.DATABASE_URL });

// 起動したときに、テーブルがなければ作る
export async function createTable() {
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
    imageUrl: `/api/items/${row.id}/image`,
  };
}
