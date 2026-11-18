import type { Product } from '../domain/types';
import type { LifestyleProfile } from './lifestyle';

/**
 * 通知に出す推薦。今はルールベースのモック。
 * 画像解析AI・位置情報ができたら、同じ形（RecommendationService）で API 呼び出しに差し替える。
 * 例: POST /api/recommendations { itemId, lifestyle, context } -> { itemId, reason, kind }
 *
 * OCRで読み取って使う予定の項目:
 *  - price         … 「¥12,800」などの価格 → お高め判定（ご褒美・お給料日の理由）
 *  - limitedUntil  … 「11/20まで」「本日23:59終了」などの期限
 *  - limitedKind   … 「コラボ」「SALE」「期間限定」などの文字 → 理由の言い回しを変える
 */
export type RecommendationKind = 'limited' | 'payday' | 'nearby' | 'genre' | 'time';
export interface Recommendation { productId: string; kind: RecommendationKind; reason: string; }
export interface RecommendationService { recommend(product: Product, profile: LifestyleProfile | null, now?: Date): Recommendation; }

const HIGH_PRICE = 10000;
const TREAT_PRICE = 5000;
const DAY = 86400000;
const startOfDay = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate());

function paydayDay(payday: string): number | null {
  if (payday.includes('月末')) return 28;
  const n = Number(payday.match(/\d{1,2}/)?.[0]);
  return n >= 1 && n <= 31 ? n : null;
}
/** 直近のお給料日から何日たったか / 次のお給料日まで何日か */
function paydayDistance(day: number, now: Date) {
  const today = startOfDay(now);
  const last = new Date(today.getFullYear(), today.getMonth(), day);
  if (last > today) last.setMonth(last.getMonth() - 1);
  const next = new Date(last); next.setMonth(next.getMonth() + 1);
  return { since: Math.round((+today - +last) / DAY), until: Math.round((+next - +today) / DAY) };
}

/** デモ用：位置情報の代わりに、ジャンルから「近くにありそうなお店」を出す */
const nearbyShop: Record<string, string> = { 'コスメ': 'ドラッグストア', '日用品': 'ドラッグストア', 'ファッション': 'よく行くセレクトショップ', '家具・インテリア': 'インテリアショップ', '暮らし': '雑貨屋さん', 'ガジェット': '家電量販店', '本・文具': '本屋さん', 'その他': '文房具屋さん' };
const genreOf: Record<string, string> = { 'コスメ': 'コスメ', 'ファッション': 'ファッション', '暮らし': '暮らし', '家具・インテリア': '暮らし', '日用品': '暮らし', 'ガジェット': 'ガジェット', '本・文具': '本・文具', 'その他': 'その他' };
const pick = <T,>(id: string, list: T[]) => list[[...id].reduce((n, c) => n + c.charCodeAt(0), 0) % list.length];

export const mockRecommendationService: RecommendationService = {
  recommend(product, profile, now = new Date()) {
    const r = (kind: RecommendationKind, reason: string): Recommendation => ({ productId: product.id, kind, reason });

    // 1. 期間限定の終わりが近い
    if (product.limitedUntil) {
      const left = Math.ceil((+new Date(product.limitedUntil) - +now) / DAY);
      if (left >= 0 && left <= 7) {
        const when = left <= 0 ? '今日まで！' : `あと${left}日`;
        if (product.limitedKind === 'collab') return r('limited', left <= 0 ? 'コラボグッズの販売期間、今日で終わりだよ！' : `コラボグッズの販売期間、終わり近づいているよ（${when}）`);
        if (product.limitedKind === 'sale') return r('limited', left <= 0 ? 'セールは今日まで！' : `セール終了まで${when}。いつもよりお得なうちに。`);
        return r('limited', left <= 0 ? '期間限定の販売が今日で終わります！' : `期間限定の販売終了まで、${when}です。`);
      }
    }
    // 2. お高めの商品 × お給料日
    const day = paydayDay(profile?.payday || '25日');
    if ((product.price ?? 0) >= HIGH_PRICE && day) {
      const { since, until } = paydayDistance(day, now);
      if (since <= 7) return r('payday', 'お高めなので、お給料が入った今がチャンス！');
      if (until <= 10) return r('payday', `お高めなので、お給料日まであと${until}日。入ったら今度こそ！`);
      return r('payday', `お高めなので、次のお給料日（${profile?.payday || '25日'}）のあとに考えるのがおすすめ。`);
    }
    // 2'. ちょっとお高め（5,000〜9,999円）× お給料日前 → ご褒美の提案
    if ((product.price ?? 0) >= TREAT_PRICE && day && paydayDistance(day, now).until <= 14) return r('payday', 'お給料日前！ちょっとお高めのこれ、ご褒美にどう？');
    // 3. 近くのお店 / よく見るジャンル / 時間がたった（デモでは商品ごとに固定で選ぶ）
    const genre = genreOf[product.category];
    const options: Recommendation[] = [r('nearby', `${nearbyShop[product.category] || 'よく行くお店'}の前を通りました。`)];
    if (profile?.favoriteGenres.includes(genre)) options.push(r('genre', `よく見る「${genre}」のアイテム。今日の気分に合うかも。`));
    const days = Math.floor((+now - +new Date(product.createdAt)) / DAY);
    if (days >= 1) options.push(r('time', `保存してから${days}日。まだ欲しい気持ち、続いてる？`));
    return pick(product.id, options);
  },
};
export const recommendationService: RecommendationService = mockRecommendationService;
