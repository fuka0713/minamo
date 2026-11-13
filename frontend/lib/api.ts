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
  imageUrl: string;
};

export type Genre = { id: string; label: string };

// 共通：API を呼んで、結果を JSON で受け取る
async function call(path: string, options?: RequestInit) {
  const res = await fetch(path, options);
  if (!res.ok) throw new Error(`エラーが起きました（${res.status}）`);
  return res.status === 204 ? null : res.json();
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

// スクショをアップロードして登録（複数枚 OK）
export function uploadScreenshots(files: File[]): Promise<Item[]> {
  const form = new FormData();
  for (const file of files) form.append("files", file);
  return call("/api/items", { method: "POST", body: form });
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

// 価格の表示（例：¥3,980）
export function showPrice(price: number | null): string {
  return price === null ? "価格不明" : `¥${price.toLocaleString()}`;
}
