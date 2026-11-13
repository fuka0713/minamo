// バックエンド（API サーバー）
// できること：スクショの登録 → 文字の読み取り → 自動でジャンル分け → 一覧・詳細・修正・削除
// ※ 中核の「思い出させる」機能（通知など）は、まだ入れていない
import express from "express";
import multer from "multer";
import { randomUUID } from "node:crypto";
import { findGenre, findPrice, findTitle, findUrl } from "./analyze.js";
import { createTable, db, toItem } from "./db.js";
import { GENRES, isGenre } from "./genres.js";
import { readText } from "./ocr.js";
import { createBucket, loadImage, removeImage, saveImage } from "./storage.js";

const app = express();
app.use(express.json());

// アップロードされた画像を、いったんメモリに置く（1枚10MBまで）
const upload = multer({ limits: { fileSize: 10 * 1024 * 1024 } });

// ジャンルの一覧
app.get("/api/genres", (req, res) => {
  res.json(GENRES.map((g) => ({ id: g.id, label: g.label })));
});

// 欲しいものの一覧（?genre=cosme&q=リップ のように絞り込める）
app.get("/api/items", async (req, res) => {
  const genre = String(req.query.genre ?? "");
  const keyword = String(req.query.q ?? "");
  const result = await db.query(
    `SELECT * FROM items
     WHERE ($1 = '' OR genre = $1)
       AND ($2 = '' OR title ILIKE '%' || $2 || '%' OR ocr_text ILIKE '%' || $2 || '%' OR memo ILIKE '%' || $2 || '%')
     ORDER BY created_at DESC`,
    [genre, keyword],
  );
  res.json(result.rows.map(toItem));
});

// スクショを登録する（複数枚まとめて OK）
app.post("/api/items", upload.array("files"), async (req, res) => {
  const files = req.files as Express.Multer.File[];
  const created = [];

  for (const file of files) {
    // 1. 画像をストレージに保存
    const imageKey = randomUUID();
    await saveImage(imageKey, file.buffer, file.mimetype);

    // 2. 画像から文字を読み取る
    const text = await readText(file.buffer);

    // 3. 文字から商品名・価格・URL・ジャンルを取り出して、データベースに保存
    const title = findTitle(text) ?? "スクショ";
    const result = await db.query(
      `INSERT INTO items (title, genre, price, url, ocr_text, image_key)
       VALUES ($1, $2, $3, $4, $5, $6) RETURNING *`,
      [title, findGenre(text), findPrice(text), findUrl(text), text, imageKey],
    );
    created.push(toItem(result.rows[0]));
  }

  res.status(201).json(created);
});

// 1件の詳細
app.get("/api/items/:id", async (req, res) => {
  const result = await db.query("SELECT * FROM items WHERE id = $1", [req.params.id]);
  if (result.rows.length === 0) return res.status(404).json({ error: "見つかりません" });
  res.json(toItem(result.rows[0]));
});

// 画像
app.get("/api/items/:id/image", async (req, res) => {
  const result = await db.query("SELECT image_key FROM items WHERE id = $1", [req.params.id]);
  if (result.rows.length === 0) return res.status(404).end();
  const image = await loadImage(result.rows[0].image_key);
  res.type(image.type).send(image.data);
});

// 修正する（送られてきた項目だけ変える）
app.patch("/api/items/:id", async (req, res) => {
  const id = req.params.id;
  const { title, price, memo, genre } = req.body;

  if (genre !== undefined) {
    if (!isGenre(genre)) return res.status(400).json({ error: "ジャンルが正しくありません" });
    // ユーザーがジャンルを直したことを記録する（genre_source = 'user'）
    await db.query("UPDATE items SET genre = $1, genre_source = 'user' WHERE id = $2", [genre, id]);
  }
  if (title !== undefined) await db.query("UPDATE items SET title = $1 WHERE id = $2", [title, id]);
  if (price !== undefined) await db.query("UPDATE items SET price = $1 WHERE id = $2", [price, id]);
  if (memo !== undefined) await db.query("UPDATE items SET memo = $1 WHERE id = $2", [memo, id]);

  const result = await db.query("SELECT * FROM items WHERE id = $1", [id]);
  if (result.rows.length === 0) return res.status(404).json({ error: "見つかりません" });
  res.json(toItem(result.rows[0]));
});

// 削除する（データベースの行と、ストレージの画像の両方）
app.delete("/api/items/:id", async (req, res) => {
  const result = await db.query("DELETE FROM items WHERE id = $1 RETURNING image_key", [req.params.id]);
  if (result.rows.length > 0) await removeImage(result.rows[0].image_key);
  res.status(204).end();
});

// 起動する
async function start() {
  // データベースとストレージが起動するまで、2秒ずつ待ちながら試す
  for (let i = 0; i < 30; i++) {
    try {
      await createTable();
      await createBucket();
      break;
    } catch {
      console.log("データベースとストレージの起動を待っています…");
      await new Promise((r) => setTimeout(r, 2000));
    }
  }
  app.listen(4000, () => console.log("backend が起動しました（ポート 4000）"));
}

start();
