export type Status = 'wanted' | 'hold' | 'bought' | 'unneeded';
export type Page = 'account' | 'diagnosis' | 'home' | 'import' | 'results' | 'wishlist' | 'detail' | 'reminders' | 'settings';
export interface Product {
  id: string;
  name: string;
  brand: string | null;
  category: string;
  price: number | null;
  currency: string | null;
  shop: string | null;
  image: string;
  description: string;
  url: string | null;
  confidence: 'high' | 'medium' | 'low';
  identification: 'sample' | 'unidentified' | 'identified';
  createdAt: string;
  /** 次に思い出す日時。予定がないとき（買った・いらない）は ''（API では null） */
  remindAt: string;
  reminderReason?: string;
  /** 期間限定・セールの終了日時（AI解析や取り込み元から取れたときだけ入る） */
  limitedUntil?: string;
  /** 期限の種類。OCRで「コラボ」「SALE」「期間限定」などの文字を読んだときに入れる */
  limitedKind?: 'limited' | 'collab' | 'sale';
  repeat: 'none' | 'daily' | 'weekly' | 'monthly';
  status: Status;
}
export interface Settings { reminders: boolean; hidePrices: boolean }
export interface SavedData { version: 1; products: Product[]; settings: Settings }
export interface ProductRepository { load(): SavedData | null; save(data: SavedData): void }
export interface Screenshot { id: string; name: string; image: string; status: 'ready' | 'analyzing' | 'done' | 'error' }
export interface AnalysisService { analyze(image: Screenshot): Promise<Product[]> }
export const categories = ['コスメ', 'ファッション', '家具・インテリア', '暮らし', '日用品', 'ガジェット', '本・文具', 'その他'];
/** ジャッジの「欲しい！」「買った！」「もういらない」と同じ言葉にそろえる */
export const statusLabels: Record<Status, string> = { wanted: '欲しい', bought: '買った', unneeded: 'もういらない', hold: '保留' };
export const repeatLabels = { none: '繰り返さない', daily: '毎日', weekly: '毎週', monthly: '毎月' };
export const isActive = (p: Product) => p.status === 'wanted' || p.status === 'hold';
export const safeUrl = (value: string | null) => { try { const u = new URL(value || ''); return ['https:', 'http:'].includes(u.protocol) ? u.href : null; } catch { return null; } };
export const dateLabel = (s: string) => !s || isNaN(+new Date(s)) ? '未設定' : new Date(s).toLocaleString('ja-JP', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' });
export const inputDate = (s: string) => { if (!s || isNaN(+new Date(s))) return ''; const d = new Date(s); return new Date(+d - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16); };
