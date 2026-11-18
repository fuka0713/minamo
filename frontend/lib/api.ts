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

// 共通：API を呼んで、結果を JSON で受け取る（エラーの文は Express は error、FastAPI は detail に入る）
// ログインしていなければ（401）、ログイン画面に移る
async function call(path: string, options?: RequestInit) {
  const res = await fetch(path, options);
  if (res.status === 401 && !path.startsWith("/api/auth/login")) {
    window.location.href = "/login";
    return new Promise(() => {}); // 画面が移るので、ここから先は何もしない
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error ?? (typeof body.detail === "string" ? body.detail : `エラーが起きました（${res.status}）`));
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

// ---- 推薦 API（いつ・どこで思い出させるか）。FastAPI が担当 ----

// 推薦：いつ知らせるとよいか（推薦日）と、その理由（推薦理由）
export type Recommendation = {
  id: number;
  itemId: number;
  recommendAt: string; // 推薦日（日時。タイムゾーンつき）
  reason: string; // 推薦理由
  basis: string; // 一番の理由（deadline, period_end, payday, place など）
  source: "gemini" | "xai" | "rules"; // 考えたもの（AI か、ルールか）
  status: "suggested" | "accepted";
  place: { name: string; lat: number | null; lng: number | null } | null; // 理由に使ったお店
  item: { id: number; title: string | null; genre: string | null; imageUrl: string } | null; // ホームの一覧のときだけ
};

// 近くで買える欲しいもの
export type NearbyMatch = {
  itemId: number;
  title: string | null;
  imageUrl: string;
  placeName: string;
  distanceM: number;
  reason: string;
  source: "gemini" | "xai" | "rules";
};

export type Position = { lat: number; lng: number };

// 推薦を作る（解析のあとに呼ぶ）。今いる場所を渡すと、近いお店を理由に使う
export function createRecommendations(itemId: number, position?: Position): Promise<{ recommendations: Recommendation[] }> {
  return sendJson(`/api/recommendations/items/${itemId}`, position ?? {});
}

// 欲しいもの1件の推薦
export function getRecommendations(itemId: number): Promise<{ recommendations: Recommendation[] }> {
  return call(`/api/recommendations/items/${itemId}`);
}

// ホーム用：見直すとよい欲しいもの（商品ごとに1つ）
export function getHomeRecommendations(limit = 4): Promise<{ recommendations: Recommendation[] }> {
  return call(`/api/recommendations?limit=${limit}`);
}

// 推薦をリマインドにする
export function acceptRecommendation(id: number): Promise<{ id: number; remindAt: string }> {
  return call(`/api/recommendations/${id}/accept`, { method: "POST" });
}

// 今いる場所の近くで買える欲しいもの
export function findNearby(position: Position): Promise<{ matches: NearbyMatch[] }> {
  return sendJson("/api/recommendations/nearby", position);
}

// 欲しいものの場所を登録する（「ここを通ったら知らせて」）
export function setPlace(itemId: number, place: { name?: string | null; lat?: number | null; lng?: number | null; radiusM?: number }) {
  return call(`/api/screenshots/${itemId}/place`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(place),
  });
}

// ブラウザの現在地（位置情報の許可が必要）。取れなければ null
export function getPosition(): Promise<Position | null> {
  return new Promise((resolve) => {
    if (!navigator.geolocation) return resolve(null);
    navigator.geolocation.getCurrentPosition(
      (p) => resolve({ lat: p.coords.latitude, lng: p.coords.longitude }),
      () => resolve(null),
      { timeout: 8000 },
    );
  });
}

// 推薦日の表示（例：11/25(水) 20:00）
export function showDateTime(iso: string): string {
  return new Date(iso).toLocaleString("ja-JP", { month: "numeric", day: "numeric", weekday: "short", hour: "2-digit", minute: "2-digit" });
}

// 考えたものの表示
export function showSource(source: string): string {
  return source === "gemini" ? "Gemini" : source === "xai" ? "Grok" : "ルール";
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
