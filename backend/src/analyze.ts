// OCR で読み取った文字から、商品名・価格・URL・ジャンルを取り出す
// （AI は使わず、キーワードと決まった形の文字だけで判定する簡単なしくみ）
import { GENRES } from "./genres.js";

// 全角の英数字（１２３、ＡＢＣ）を半角にそろえる
function normalize(text: string): string {
  return text.normalize("NFKC");
}

// 価格：「¥3,980」や「3,980円」を探して数字にする
export function findPrice(text: string): number | null {
  const match = normalize(text).match(/[¥￥]\s*([0-9,]+)|([0-9,]+)\s*円/);
  if (!match) return null;
  const price = Number((match[1] ?? match[2]).replace(/,/g, ""));
  return price > 0 ? price : null;
}

// URL：「https://...」を探す
export function findUrl(text: string): string | null {
  const match = normalize(text).match(/https?:\/\/\S+/);
  return match ? match[0] : null;
}

// 商品名：上から見て、最初の「ちゃんとした文字の行」を使う
// （時刻や電池の％、価格だけの行、URL の行は飛ばす）
export function findTitle(text: string): string | null {
  const lines = normalize(text).split("\n").map((line) => line.trim());
  for (const line of lines) {
    if (line.length < 2) continue; // 短すぎる
    if (/^[0-9:%\s]+$/.test(line)) continue; // 「12:34」「80%」など
    if (/https?:\/\//.test(line)) continue; // URL
    if (findPrice(line) !== null && line.length < 15) continue; // 価格だけの行
    if (!/\p{L}/u.test(line)) continue; // 文字がない（記号だけ）
    return line.slice(0, 40);
  }
  return null;
}

// ジャンル：キーワードが一番多く見つかったジャンルにする（なければ「その他」）
export function findGenre(text: string): string {
  const t = normalize(text);
  let bestGenre = "other";
  let bestCount = 0;
  for (const genre of GENRES) {
    const count = genre.keywords.filter((word) => t.includes(word)).length;
    if (count > bestCount) {
      bestGenre = genre.id;
      bestCount = count;
    }
  }
  return bestGenre;
}
