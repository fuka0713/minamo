"use client";

// トップページ：スクショのアップロードと、欲しいものリスト（一覧）
import Link from "next/link";
import { useEffect, useState } from "react";
import {
  analyzeScreenshot,
  createRecommendations,
  findNearby,
  getGenres,
  getHomeRecommendations,
  getItems,
  getMe,
  getPosition,
  logout,
  registerScreenshots,
  showDateTime,
  showPeriod,
  showPrice,
  showSource,
  type Genre,
  type Item,
  type NearbyMatch,
  type Recommendation,
} from "@/lib/api";

export default function Home() {
  const [genres, setGenres] = useState<Genre[]>([]); // ジャンルの一覧
  const [items, setItems] = useState<Item[]>([]); // 欲しいものの一覧
  const [genre, setGenre] = useState(""); // 選んでいるジャンル（"" = すべて）
  const [keyword, setKeyword] = useState(""); // 検索キーワード
  const [message, setMessage] = useState(""); // 画面に出すお知らせ
  const [email, setEmail] = useState(""); // ログインしている人
  const [recs, setRecs] = useState<Recommendation[]>([]); // 見直すとよい欲しいもの（推薦）
  const [nearby, setNearby] = useState<NearbyMatch[] | null>(null); // 近くで買える欲しいもの

  // 最初に1回だけ：ログインしている人と、ジャンルの一覧を読み込む
  // （ログインしていなければ、自動でログイン画面に移る）
  useEffect(() => {
    getMe().then((user) => setEmail(user.email));
    getGenres().then(setGenres);
    getHomeRecommendations().then((r) => setRecs(r.recommendations));
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
    // 2. 1枚ずつ解析して（解析 API）、商品名・ジャンルなどを埋める
    // 3. 続けて推薦を作る（推薦 API）：いつ思い出させるか・その理由。1つが自動でリマインドになる
    for (let i = 0; i < created.length; i++) {
      setMessage(`解析中…（${i + 1}/${created.length}枚）`);
      await analyzeScreenshot(created[i].id);
      await createRecommendations(created[i].id);
    }
    setMessage(`${created.length}枚を登録しました`);
    setItems(await getItems(genre, keyword));
    setRecs((await getHomeRecommendations()).recommendations);
  }

  // 近くで買える欲しいものを調べる（位置情報が取れなければ、仮の場所＝新宿駅で調べる）
  async function handleNearby() {
    setMessage("近くのお店を調べています…");
    const position = (await getPosition()) ?? { lat: 35.6896, lng: 139.7006 };
    const result = await findNearby(position);
    setNearby(result.matches);
    setMessage("");
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

      {/* 推薦：眠ってる「欲しい」を起こす（推薦 API） */}
      <section className="space-y-2 rounded-xl bg-emerald-50 p-4">
        <div className="flex items-center justify-between">
          <h2 className="font-bold">🐈 眠ってる「欲しい」を起こしてみる？</h2>
          <button onClick={handleNearby} className="chip">
            📍 近くで買えるもの
          </button>
        </div>
        {nearby !== null && (
          <div className="space-y-1 text-sm">
            {nearby.length === 0 && <p className="text-gray-500">近くで買えるものは、今はありません。</p>}
            {nearby.map((m) => (
              <Link key={m.itemId} href={`/items/${m.itemId}`} className="block rounded-lg bg-white p-2">
                📍 <b>{m.placeName}</b>（約{m.distanceM}m）：{m.reason}
              </Link>
            ))}
          </div>
        )}
        {recs.length === 0 && <p className="text-sm text-gray-500">スクショを追加すると、思い出すとよい日をおすすめします。</p>}
        <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
          {recs.map((r) => (
            <Link key={r.id} href={`/items/${r.itemId}`} className="flex gap-3 rounded-lg bg-white p-2 text-sm">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              {r.item && <img src={r.item.imageUrl} alt="" className="h-16 w-16 rounded object-cover object-top" />}
              <div>
                <p className="font-bold">{r.item?.title || "（商品名なし）"}</p>
                <p className="text-emerald-700">🔔 {showDateTime(r.recommendAt)}</p>
                <p className="text-gray-600">{r.reason}</p>
                <p className="text-xs text-gray-400">考えたもの：{showSource(r.source)}</p>
              </div>
            </Link>
          ))}
        </div>
      </section>

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
