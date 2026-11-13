"use client";

// 詳細画面：自動で分けたジャンルが違うときに、ユーザーが直せる（UC13）
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { deleteItem, getGenres, getItem, showPrice, updateItem, type Genre, type Item } from "@/lib/api";

export default function ItemDetail({ id }: { id: string }) {
  const router = useRouter();
  const [item, setItem] = useState<Item | null>(null);
  const [genres, setGenres] = useState<Genre[]>([]);
  const [message, setMessage] = useState("");

  // 最初に1回だけ：この商品とジャンルの一覧を読み込む
  useEffect(() => {
    getItem(id).then(setItem);
    getGenres().then(setGenres);
  }, [id]);

  if (!item) return <p>読み込み中…</p>;

  // 入力欄の内容を、画面の中の item に反映する（保存はまだ）
  function edit(changes: Partial<Item>) {
    setItem({ ...item!, ...changes });
  }

  async function save() {
    setItem(await updateItem(item!.id, { title: item!.title, price: item!.price, memo: item!.memo }));
    setMessage("保存しました");
  }

  async function changeGenre(genre: string) {
    setItem(await updateItem(item!.id, { genre }));
    setMessage("ジャンルを修正しました");
  }

  async function remove() {
    if (!confirm("削除しますか？")) return;
    await deleteItem(item!.id);
    router.push("/");
  }

  return (
    <div className="space-y-4">
      <Link href="/" className="text-sm text-gray-500">
        ← 一覧に戻る
      </Link>

      <div className="grid gap-6 md:grid-cols-2">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={item.imageUrl} alt="" className="w-full rounded-xl border border-gray-200" />

        <div className="space-y-4">
          <p className="text-sm text-gray-500">
            ジャンル（{item.genreSource === "auto" ? "システムが自動で分類" : "修正済み"}）
          </p>
          <select value={item.genre} onChange={(e) => changeGenre(e.target.value)} className="input">
            {genres.map((g) => (
              <option key={g.id} value={g.id}>
                {g.label}
              </option>
            ))}
          </select>

          <p className="text-sm text-gray-500">商品名</p>
          <input value={item.title} onChange={(e) => edit({ title: e.target.value })} className="input" />

          <p className="text-sm text-gray-500">価格（いま：{showPrice(item.price)}）</p>
          <input
            value={item.price ?? ""}
            onChange={(e) => edit({ price: e.target.value === "" ? null : Number(e.target.value) })}
            type="number"
            className="input"
          />

          <p className="text-sm text-gray-500">メモ</p>
          <textarea value={item.memo} onChange={(e) => edit({ memo: e.target.value })} className="input" />

          <div className="flex gap-2">
            <button onClick={save} className="chip chip-on">
              保存
            </button>
            <button onClick={remove} className="chip text-red-600">
              削除
            </button>
          </div>
          {message && <p className="text-sm">{message}</p>}

          <details>
            <summary className="text-sm text-gray-500">読み取った文字（OCR）</summary>
            <pre className="whitespace-pre-wrap text-xs">{item.ocrText || "（読み取れませんでした）"}</pre>
          </details>
        </div>
      </div>
    </div>
  );
}
