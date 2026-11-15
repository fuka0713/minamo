// バックエンド（API サーバー）
// できること：アカウント登録・ログイン → スクショの登録 → 文字の読み取り
//            → 自動でジャンル分け・期間の読み取り → 一覧・詳細・修正・削除
// スクショや欲しいものは、ログインしている人ごとに分かれる
// ※ 中核の「通知」はまだ入れていない
import express from "express";
import multer from "multer";
import { randomUUID } from "node:crypto";
import { findGenre, findPeriod, findPrice, findTitle, findUrl } from "./analyze.js";
import { login, logout, me, requireLogin, signup } from "./auth.js";
import { createTables, db, toItem } from "./db.js";
import { GENRES, isGenre } from "./genres.js";
import { readText } from "./ocr.js";
import { createBucket, loadImage, removeImage, saveImage } from "./storage.js";

const app = express();
app.use(express.json());

// アップロードされた画像を、いったんメモリに置く（1枚10MBまで）
const upload = multer({ limits: { fileSize: 10 * 1024 * 1024 } });

// ---- アカウント（ログインしていなくても使える） ----
app.post("/api/auth/signup", signup);
app.post("/api/auth/login", login);
app.post("/api/auth/logout", logout);

// ジャンルの一覧（ログインしていなくても使える）
app.get("/api/genres", (req, res) => {
  res.json(GENRES.map((g) => ({ id: g.id, label: g.label })));
});

// ---- ここから下は、ログインが必要 ----
app.use("/api", requireLogin);

// ログインしている人の情報
app.get("/api/auth/me", me);

// 欲しいものの一覧（?genre=cosme&q=リップ のように絞り込める）。自分の分だけ
app.get("/api/items", async (req, res) => {
  const genre = String(req.query.genre ?? "");
  const keyword = String(req.query.q ?? "");
  const result = await db.query(
    `SELECT * FROM items
     WHERE user_id = $1
       AND ($2 = '' OR genre = $2)
       AND ($3 = '' OR title ILIKE '%' || $3 || '%' OR ocr_text ILIKE '%' || $3 || '%' OR memo ILIKE '%' || $3 || '%')
     ORDER BY created_at DESC`,
    [res.locals.userId, genre, keyword],
  );
  res.json(result.rows.map(toItem));
});

// スクショを登録する（複数枚まとめて OK）
app.post("/api/items", upload.array("files"), async (req, res) => {
  const files = req.files as Express.Multer.File[];
  const created = [];

  for (const file of files) {
    // 1. 画像をストレージに保存（人ごとにフォルダを分ける）
    const imageKey = `users/${res.locals.userId}/${randomUUID()}`;
    await saveImage(imageKey, file.buffer, file.mimetype);

    // 2. 画像から文字を読み取る
    const text = await readText(file.buffer);

    // 3. 文字から商品名・価格・URL・ジャンル・期間を取り出して、データベースに保存
    const title = findTitle(text) ?? "スクショ";
    const period = findPeriod(text);
    const result = await db.query(
      `INSERT INTO items (user_id, title, genre, price, url, ocr_text, image_key, period_start, period_end, deadline, release_date)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11) RETURNING *`,
      [res.locals.userId, title, findGenre(text), findPrice(text), findUrl(text), text, imageKey,
       period.start, period.end, period.deadline, period.release],
    );
    created.push(toItem(result.rows[0]));
  }

  res.status(201).json(created);
});

// 1件の詳細（自分のものだけ）
app.get("/api/items/:id", async (req, res) => {
  const result = await db.query("SELECT * FROM items WHERE id = $1 AND user_id = $2", [req.params.id, res.locals.userId]);
  if (result.rows.length === 0) return res.status(404).json({ error: "見つかりません" });
  res.json(toItem(result.rows[0]));
});

// 画像（自分のものだけ）
app.get("/api/items/:id/image", async (req, res) => {
  const result = await db.query("SELECT image_key FROM items WHERE id = $1 AND user_id = $2", [req.params.id, res.locals.userId]);
  if (result.rows.length === 0) return res.status(404).end();
  const image = await loadImage(result.rows[0].image_key);
  res.type(image.type).send(image.data);
});

// 「YYYY-MM-DD」か null なら OK
function isDateOrNull(value: unknown): boolean {
  return value === null || (typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value));
}

// 修正する（送られてきた項目だけ変える。自分のものだけ）
app.patch("/api/items/:id", async (req, res) => {
  const found = await db.query("SELECT id FROM items WHERE id = $1 AND user_id = $2", [req.params.id, res.locals.userId]);
  if (found.rows.length === 0) return res.status(404).json({ error: "見つかりません" });
  const id = found.rows[0].id;
  const { title, price, memo, genre, period } = req.body;

  if (genre !== undefined) {
    if (!isGenre(genre)) return res.status(400).json({ error: "ジャンルが正しくありません" });
    // ユーザーがジャンルを直したことを記録する（genre_source = 'user'）
    await db.query("UPDATE items SET genre = $1, genre_source = 'user' WHERE id = $2", [genre, id]);
  }
  if (period !== undefined) {
    const { start = null, end = null, deadline = null, release = null } = period;
    if (![start, end, deadline, release].every(isDateOrNull)) {
      return res.status(400).json({ error: "日付は YYYY-MM-DD の形にしてください" });
    }
    // ユーザーが期間を直したことを記録する（period_source = 'user'）
    await db.query(
      `UPDATE items SET period_start = $1, period_end = $2, deadline = $3, release_date = $4, period_source = 'user'
       WHERE id = $5`,
      [start, end, deadline, release, id],
    );
  }
  if (title !== undefined) await db.query("UPDATE items SET title = $1 WHERE id = $2", [title, id]);
  if (price !== undefined) await db.query("UPDATE items SET price = $1 WHERE id = $2", [price, id]);
  if (memo !== undefined) await db.query("UPDATE items SET memo = $1 WHERE id = $2", [memo, id]);

  const result = await db.query("SELECT * FROM items WHERE id = $1", [id]);
  res.json(toItem(result.rows[0]));
});

// 削除する（データベースの行と、ストレージの画像の両方。自分のものだけ）
app.delete("/api/items/:id", async (req, res) => {
  const result = await db.query(
    "DELETE FROM items WHERE id = $1 AND user_id = $2 RETURNING image_key",
    [req.params.id, res.locals.userId],
  );
  if (result.rows.length > 0) await removeImage(result.rows[0].image_key);
  res.status(204).end();
});

// 起動する
async function start() {
  // データベースとストレージが起動するまで、2秒ずつ待ちながら試す
  for (let i = 0; i < 30; i++) {
    try {
      await createTables();
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
