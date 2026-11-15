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

// ---------------------------------------------------------------
// 期間：コラボの開催期間・締切・発売日を読み取る
//   例）「11/1(金)〜11/30(土)」「2026年12月5日 23:59 締切」「12/20 発売」
//   年が書いていない日付は、今年（すでに大きく過ぎていれば来年）とみなす
// ---------------------------------------------------------------
export type Period = {
  start: string | null; // 開催・販売が始まる日（YYYY-MM-DD）
  end: string | null; // 終わる日
  deadline: string | null; // 受注・予約の締切
  release: string | null; // 発売日・公開日
};

// 「2026年11月1日」「2026.11.1」「11月1日」を「2026/11/1」「11/1」の形にそろえる
function unifyDates(text: string): string {
  return normalize(text)
    .replace(/(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日?/g, "$1/$2/$3")
    .replace(/(\d{1,2})\s*月\s*(\d{1,2})\s*日?/g, "$1/$2")
    .replace(/(\d{4})\.(\d{1,2})\.(\d{1,2})/g, "$1/$2/$3");
}

// 年・月・日から「YYYY-MM-DD」を作る（年がなければ today をもとに決める）
function makeDate(year: string | undefined, month: string, day: string, today: Date): string | null {
  const m = Number(month);
  const d = Number(day);
  if (m < 1 || m > 12 || d < 1 || d > 31) return null;
  let y = year ? Number(year) : today.getFullYear();
  if (!year) {
    // 2か月以上前の日付になってしまうなら、来年のことだと考える
    const candidate = new Date(y, m - 1, d);
    if (today.getTime() - candidate.getTime() > 60 * 24 * 60 * 60 * 1000) y += 1;
  }
  return `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
}

// 日付1つ分の形：「2026/11/1」または「11/1」。後ろに曜日「(金)」や時刻「23:59」が付いてもよい
const DATE = String.raw`(?:(\d{4})\/)?(\d{1,2})\/(\d{1,2})(?:\s*[(（][^)）]{1,3}[)）])?(?:\s*\d{1,2}:\d{2})?`;

export function findPeriod(text: string, today = new Date()): Period {
  const t = unifyDates(text);
  const period: Period = { start: null, end: null, deadline: null, release: null };

  // 開催期間：「日付 〜 日付」（終わりの日付は「30日」のように日だけでもよい）
  const range = t.match(new RegExp(`${DATE}\\s*(?:〜|~|-|–|—|から)\\s*(?:${DATE}|(\\d{1,2})日?)`));
  if (range) {
    const [, y1, m1, d1, y2, m2, d2, dayOnly] = range;
    period.start = makeDate(y1, m1, d1, today);
    if (m2) {
      // 終わりの月が始まりの月より前なら、年をまたいでいる（12/20〜1/10 など）
      const endYear = y2 ?? (Number(m2) < Number(m1) && period.start ? String(Number(period.start.slice(0, 4)) + 1) : period.start?.slice(0, 4));
      period.end = makeDate(endYear, m2, d2, today);
    } else if (dayOnly) {
      period.end = makeDate(period.start?.slice(0, 4), m1, dayOnly, today);
    }
  }

  // 締切：「締切 12/5」「12/5 締切」「受注締切：12/5」
  const deadline =
    t.match(new RegExp(`(?:締切|締め切り|〆切|受付終了|受注終了)[:：\\s]*${DATE}`)) ??
    t.match(new RegExp(`${DATE}\\s*(?:締切|締め切り|〆切|受付終了|受注終了)`));
  if (deadline) period.deadline = makeDate(deadline[1], deadline[2], deadline[3], today);

  // 発売日：「発売日 12/20」「12/20 発売」「公開日：12/20」
  const release =
    t.match(new RegExp(`(?:発売日|発売|公開日|公開|配信開始)[:：\\s]*${DATE}`)) ??
    t.match(new RegExp(`${DATE}\\s*(?:発売|公開|配信開始)`));
  if (release) period.release = makeDate(release[1], release[2], release[3], today);

  // 期間がなく「12/24まで」とだけある場合は、終わる日とみなす
  if (!period.end) {
    const until = t.match(new RegExp(`${DATE}\\s*まで`));
    if (until) period.end = makeDate(until[1], until[2], until[3], today);
  }

  return period;
}
