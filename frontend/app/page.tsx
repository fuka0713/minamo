"use client";

// トップページ：スクショのアップロードと、欲しいものリスト（一覧）
import Link from "next/link";
import { useEffect, useState } from "react";
import { analyzeScreenshot, getGenres, getItems, getMe, logout, registerScreenshots, showPeriod, showPrice, type Genre, type Item } from "@/lib/api";

export default function Home() {
  const [genres, setGenres] = useState<Genre[]>([]); // ジャンルの一覧
  const [items, setItems] = useState<Item[]>([]); // 欲しいものの一覧
  const [genre, setGenre] = useState(""); // 選んでいるジャンル（"" = すべて）
  const [keyword, setKeyword] = useState(""); // 検索キーワード
  const [message, setMessage] = useState(""); // 画面に出すお知らせ
  const [email, setEmail] = useState(""); // ログインしている人

  // 最初に1回だけ：ログインしている人と、ジャンルの一覧を読み込む
  // （ログインしていなければ、自動でログイン画面に移る）
  useEffect(() => {
    getMe().then((user) => setEmail(user.email));
    getGenres().then(setGenres);
  }, []);

  // ジャンルかキーワードが変わったら：一覧を読み込み直す
  useEffect(() => {
    getItems(genre, keyword).then(setItems);
  }, [genre, keyword]);

  // スクショが選ばれたとき
  async function handleUpload(files: FileList | null) {
    if (!files || files.length === 0) return;
    // 1. 登録（登録した日と画像だけ）→ すぐ一覧に「解析中…」で出す
    const created = await registerScreenshots(Array.from(files));
    setItems(await getItems(genre, keyword));
    // 2. 1枚ずつ解析して、商品名・ジャンルなどを埋める
    for (let i = 0; i < created.length; i++) {
      setMessage(`解析中…（${i + 1}/${created.length}枚）`);
      await analyzeScreenshot(created[i].id);
    }
    setMessage(`${created.length}枚を登録しました`);
    setItems(await getItems(genre, keyword));
  }

  async function handleLogout() {
    await logout();
    window.location.href = "/login";
  }

  // ジャンルの id から表示名を探す（例：cosme → コスメ）
  function genreLabel(id: string) {
    return genres.find((g) => g.id === id)?.label ?? id;
  }

  return (
    <div className="space-y-6">
      {/* ログインしている人 */}
      <div className="flex items-center justify-end gap-3 text-sm text-gray-500">
        <span>{email}</span>
        <button onClick={handleLogout} className="underline">
          ログアウト
        </button>
      </div>

      {/* アップロード */}
      <label className="block cursor-pointer rounded-xl border-2 border-dashed border-gray-300 p-6 text-center">
        <input type="file" accept="image/*" multiple className="hidden" onChange={(e) => handleUpload(e.target.files)} />
        <p className="font-bold">📸 スクショを追加</p>
        <p className="text-sm text-gray-500">クリックして選ぶ（複数枚OK）</p>
      </label>
      {message && <p className="text-sm">{message}</p>}

      {/* 検索とジャンルの絞り込み */}
      <input
        value={keyword}
        onChange={(e) => setKeyword(e.target.value)}
        placeholder="キーワードで探す"
        className="input"
      />
      <div className="flex flex-wrap gap-2">
        <button onClick={() => setGenre("")} className={genre === "" ? "chip chip-on" : "chip"}>
          すべて
        </button>
        {genres.map((g) => (
          <button key={g.id} onClick={() => setGenre(g.id)} className={genre === g.id ? "chip chip-on" : "chip"}>
            {g.label}
          </button>
        ))}
      </div>

      {/* 一覧 */}
      {items.length === 0 && <p className="text-gray-500">まだ欲しいものがありません。</p>}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {items.map((item) => (
          <Link key={item.id} href={`/items/${item.id}`} className="rounded-xl border border-gray-200">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={item.imageUrl} alt="" className="aspect-[3/4] w-full object-cover object-top" />
            <div className="p-2 text-sm">
              <p className="font-bold">{item.analysisStatus === "pending" ? "解析中…" : item.title || "（商品名なし）"}</p>
              <p className="text-gray-500">
                {genreLabel(item.genre)}
                {item.priceVisible && item.price !== null && `・${showPrice(item.price)}`}
              </p>
              {showPeriod(item.period) && <p className="text-orange-600">📅 {showPeriod(item.period)}</p>}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
