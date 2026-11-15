// バックエンドの API を呼ぶための関数をまとめたファイル

export type Item = {
  id: number;
  title: string; // 商品名
  genre: string; // ジャンル（cosme, fashion など）
  genreSource: "auto" | "user"; // auto = システムが自動で分類 / user = ユーザーが修正
  price: number | null; // 価格（読み取れなければ null）
  url: string | null;
  ocrText: string; // 読み取った文字
  memo: string;
  description: string | null; // 説明文（解析で埋まる）
  wishStatus: "want" | "not_want" | "pending"; // いる / いらない / 保留
  priceVisible: boolean; // 価格を表示するか（最初は表示しない）
  analysisStatus: "pending" | "done" | "failed"; // 解析の状態
  period: Period; // OCR で読み取った期間（ユーザーが直すこともできる）
  imageUrl: string;
};

// 日付は「YYYY-MM-DD」の文字（なければ null）
export type Period = {
  start: string | null; // 開催・販売が始まる日
  end: string | null; // 終わる日
  deadline: string | null; // 受注・予約の締切
  release: string | null; // 発売日
  source?: "auto" | "user"; // auto = 自動で読み取り / user = ユーザーが修正
};

export type User = { id: number; email: string };

export type Genre = { id: string; label: string };

// 共通：API を呼んで、結果を JSON で受け取る
// ログインしていなければ（401）、ログイン画面に移る
async function call(path: string, options?: RequestInit) {
  const res = await fetch(path, options);
  if (res.status === 401 && !path.startsWith("/api/auth/login")) {
    window.location.href = "/login";
    return new Promise(() => {}); // 画面が移るので、ここから先は何もしない
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error ?? `エラーが起きました（${res.status}）`);
  }
  return res.status === 204 ? null : res.json();
}

// ---- アカウント ----
function sendJson(path: string, body: unknown) {
  return call(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
}

// アカウント登録（登録するとそのままログインした状態になる）
export function signup(email: string, password: string): Promise<User> {
  return sendJson("/api/auth/signup", { email, password });
}

// ログイン
export function login(email: string, password: string): Promise<User> {
  return sendJson("/api/auth/login", { email, password });
}

// ログアウト
export function logout(): Promise<null> {
  return call("/api/auth/logout", { method: "POST" });
}

// ログインしている人
export function getMe(): Promise<User> {
  return call("/api/auth/me");
}

// ジャンルの一覧
export function getGenres(): Promise<Genre[]> {
  return call("/api/genres");
}

// 欲しいものの一覧（ジャンルとキーワードで絞り込み）
export function getItems(genre: string, keyword: string): Promise<Item[]> {
  const params = new URLSearchParams({ genre, q: keyword });
  return call(`/api/items?${params}`);
}

// 1件の詳細
export function getItem(id: string): Promise<Item> {
  return call(`/api/items/${id}`);
}

// スクショを登録する（複数枚 OK）。登録した日と画像だけが入る。FastAPI が担当
export function registerScreenshots(files: File[]): Promise<{ id: number }[]> {
  const form = new FormData();
  for (const file of files) form.append("files", file);
  return call("/api/screenshots", { method: "POST", body: form });
}

// 登録したスクショを解析して、商品名・ジャンルなどを埋める。FastAPI が担当
export function analyzeScreenshot(id: number): Promise<{ analysis: { status: string } }> {
  return call(`/api/screenshots/${id}/analyze`, { method: "POST" });
}

// 修正（ジャンル・商品名・価格・メモ）
export function updateItem(id: number, changes: Partial<Item>): Promise<Item> {
  return call(`/api/items/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(changes),
  });
}

// 削除
export function deleteItem(id: number): Promise<null> {
  return call(`/api/items/${id}`, { method: "DELETE" });
}

// 期間の表示（例：11/1〜11/30、締切 12/5、発売 12/20）
export function showPeriod(period: Period): string {
  const md = (date: string) => `${Number(date.slice(5, 7))}/${Number(date.slice(8, 10))}`;
  const parts = [];
  if (period.start || period.end) parts.push(`${period.start ? md(period.start) : ""}〜${period.end ? md(period.end) : ""}`);
  if (period.deadline) parts.push(`締切 ${md(period.deadline)}`);
  if (period.release) parts.push(`発売 ${md(period.release)}`);
  return parts.join("・");
}

// 価格の表示（例：¥3,980）。間違っているとストレスなので、表示する設定のときだけ出す
export function showPrice(price: number | null, visible = true): string {
  if (!visible || price === null) return "";
  return `¥${price.toLocaleString()}`;
}
