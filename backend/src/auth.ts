// アカウント（登録・ログイン・ログアウト）
// ログインすると、ブラウザのクッキーに「session=合言葉」が入る。
// 以降のリクエストでは、その合言葉から「誰か」を調べる。
import type { NextFunction, Request, Response } from "express";
import { randomBytes, scryptSync, timingSafeEqual } from "node:crypto";
import { db } from "./db.js";

// パスワードは、そのままではなく「ハッシュ（元に戻せない形）」にして保存する
function hashPassword(password: string): string {
  const salt = randomBytes(16).toString("hex");
  const hash = scryptSync(password, salt, 64).toString("hex");
  return `${salt}:${hash}`;
}

function checkPassword(password: string, saved: string): boolean {
  const [salt, hash] = saved.split(":");
  const input = scryptSync(password, salt, 64);
  return timingSafeEqual(input, Buffer.from(hash, "hex"));
}

// ログイン中の印を作って、クッキーに入れる（30日間有効）
async function startSession(res: Response, userId: number) {
  const token = randomBytes(32).toString("hex");
  await db.query("INSERT INTO sessions (token, user_id) VALUES ($1, $2)", [token, userId]);
  res.setHeader("Set-Cookie", `session=${token}; HttpOnly; Path=/; SameSite=Lax; Max-Age=${60 * 60 * 24 * 30}`);
}

// リクエストのクッキーから「session=…」を取り出す
function getToken(req: Request): string | null {
  const cookie = req.headers.cookie ?? "";
  const match = cookie.match(/(?:^|;\s*)session=([a-f0-9]+)/);
  return match ? match[1] : null;
}

// アカウント登録
export async function signup(req: Request, res: Response) {
  const email = String(req.body?.email ?? "").trim().toLowerCase();
  const password = String(req.body?.password ?? "");
  if (!email.includes("@")) return res.status(400).json({ error: "メールアドレスを入れてください" });
  if (password.length < 8) return res.status(400).json({ error: "パスワードは8文字以上にしてください" });

  const exists = await db.query("SELECT id FROM users WHERE email = $1", [email]);
  if (exists.rows.length > 0) return res.status(409).json({ error: "このメールアドレスはもう登録されています" });

  const result = await db.query(
    "INSERT INTO users (email, password_hash) VALUES ($1, $2) RETURNING id, email",
    [email, hashPassword(password)],
  );
  await startSession(res, result.rows[0].id);
  res.status(201).json(result.rows[0]);
}

// ログイン
export async function login(req: Request, res: Response) {
  const email = String(req.body?.email ?? "").trim().toLowerCase();
  const password = String(req.body?.password ?? "");
  const result = await db.query("SELECT * FROM users WHERE email = $1", [email]);
  const user = result.rows[0];
  if (!user || !checkPassword(password, user.password_hash)) {
    return res.status(401).json({ error: "メールアドレスかパスワードが違います" });
  }
  await startSession(res, user.id);
  res.json({ id: user.id, email: user.email });
}

// ログアウト
export async function logout(req: Request, res: Response) {
  const token = getToken(req);
  if (token) await db.query("DELETE FROM sessions WHERE token = $1", [token]);
  res.setHeader("Set-Cookie", "session=; HttpOnly; Path=/; SameSite=Lax; Max-Age=0");
  res.status(204).end();
}

// ログインしている人の情報
export async function me(req: Request, res: Response) {
  const result = await db.query("SELECT id, email FROM users WHERE id = $1", [res.locals.userId]);
  res.json(result.rows[0]);
}

// ログインが必要な API の前に置く「門番」。ログインしていなければ 401 を返す
export async function requireLogin(req: Request, res: Response, next: NextFunction) {
  const token = getToken(req);
  const result = token ? await db.query("SELECT user_id FROM sessions WHERE token = $1", [token]) : { rows: [] };
  if (result.rows.length === 0) return res.status(401).json({ error: "ログインしてください" });
  res.locals.userId = result.rows[0].user_id; // 以降の処理で「誰か」が分かる
  next();
}
