/**
 * バックエンド（FastAPI）とのやりとりを、ここに集めています。
 * 画面は Product など画面用の形だけを使い、APIの形との変換はこのファイルで行います。
 * ログインはクッキー（session）なので、トークンを画面側で持つ必要はありません。
 */
import type { Product, Settings, Status } from '../domain/types';
import type { LifestyleProfile } from './lifestyle';

const BASE = import.meta.env.VITE_API_BASE_URL || '/api';

/** API が返すエラー（{"error": {code, message, requestId}}）。 */
export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) { super(message); }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = init.body && !(init.body instanceof FormData) ? { 'Content-Type': 'application/json' } : undefined;
  let res: Response;
  try {
    res = await fetch(BASE + path, { credentials: 'same-origin', headers, ...init });
  } catch {
    throw new ApiError(0, 'NETWORK', 'サーバーにつながりませんでした。通信状況を確認してください。');
  }
  if (res.status === 204) return undefined as T;
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const e = body?.error;
    throw new ApiError(res.status, e?.code || 'UNKNOWN', e?.message || `エラーが起きました（${res.status}）`);
  }
  return body as T;
}
const json = (method: string, data: unknown): RequestInit => ({ method, body: JSON.stringify(data) });

// ---------- APIの形 ----------
interface ItemOut {
  id: string; name: string; brand: string | null; genre: string; price: number | null; currency: string | null;
  shop: string | null; url: string | null; period: { type: string; startAt: string | null; endAt: string | null } | null;
  identification: 'identified' | 'unidentified'; confidence: number; status: 'wanted' | 'hold' | 'bought' | 'unwanted';
  memo: string; createdAt: string; remindAt: string | null; imageUrl: string; reminderReason: string | null;
  repeat: Product['repeat']; limitedUntil: string | null; limitedKind: Product['limitedKind'] | null;
}
interface NotificationOut { id: string; itemId: string; message: string; status: 'unread' | 'answered'; item: ItemOut | null }
export interface User { id: string; username: string; email: string }

// ---------- 形の変換 ----------
const toStatus = (s: ItemOut['status']): Status => (s === 'unwanted' ? 'unneeded' : s);
const fromStatus = (s: Status): ItemOut['status'] => (s === 'unneeded' ? 'unwanted' : s);

/** API の商品 → 画面の商品。確かさ（0〜1）は「高・中・低」の3段階にします。 */
export function toProduct(i: ItemOut): Product {
  return {
    id: i.id, name: i.name, brand: i.brand, category: i.genre, price: i.price, currency: i.currency, shop: i.shop,
    image: i.imageUrl, description: i.memo, url: i.url,
    confidence: i.confidence >= 0.7 ? 'high' : i.confidence >= 0.4 ? 'medium' : 'low',
    identification: i.identification, createdAt: i.createdAt, remindAt: i.remindAt ?? '',
    reminderReason: i.reminderReason || undefined, repeat: i.repeat, status: toStatus(i.status),
    limitedUntil: i.limitedUntil ?? undefined, limitedKind: i.limitedKind ?? undefined,
  };
}

// ---------- アカウント ----------
export const authApi = {
  me: () => request<User>('/auth/me'),
  login: (username: string, password: string) => request<User>('/auth/login', json('POST', { username, password })),
  signup: (username: string, password: string) => request<User>('/auth/signup', json('POST', { username, password })),
  logout: () => request<void>('/auth/logout', { method: 'POST' }),
  /** デモ：メールアドレスとパスワードなしで入る（このブラウザだけのアカウント） */
  guest: () => request<User>('/auth/guest', { method: 'POST' }),
};

// ---------- 欲しいもの ----------
export const itemApi = {
  /** すべての商品を読みます（ページを最後までたどる）。 */
  async listAll(): Promise<Product[]> {
    const all: Product[] = [];
    let cursor: string | null = null;
    do {
      const q: string = cursor ? `&cursor=${encodeURIComponent(cursor)}` : '';
      const page: { items: ItemOut[]; nextCursor: string | null } = await request(`/items?limit=100${q}`);
      all.push(...page.items.map(toProduct));
      cursor = page.nextCursor;
    } while (cursor);
    return all;
  },
  /** スクショを送ると、サーバーが解析して登録し、商品が返ります。 */
  async upload(image: Blob, filename: string): Promise<Product> {
    const form = new FormData();
    form.append('image', image, filename);
    return toProduct(await request<ItemOut>('/items', { method: 'POST', body: form }));
  },
  /** 変わった項目だけを送ります。リマインド日時が変わったときは、予定を入れ直します。 */
  async save(before: Product, after: Product): Promise<Product> {
    const patch: Record<string, unknown> = {};
    if (after.name !== before.name) patch.name = after.name;
    if (after.brand !== before.brand) patch.brand = after.brand;
    if (after.category !== before.category) patch.genre = after.category;
    if (after.price !== before.price) patch.price = after.price;
    if (after.currency !== before.currency) patch.currency = after.currency;
    if (after.shop !== before.shop) patch.shop = after.shop;
    if (after.url !== before.url) patch.url = after.url;
    if (after.description !== before.description) patch.memo = after.description;
    if (after.repeat !== before.repeat) patch.repeat = after.repeat;
    if (after.status !== before.status) patch.status = fromStatus(after.status);
    let saved = before;
    if (Object.keys(patch).length) saved = toProduct(await request<ItemOut>(`/items/${before.id}`, json('PATCH', patch)));
    if (after.remindAt && after.remindAt !== before.remindAt && (after.status === 'wanted' || after.status === 'hold')) {
      saved = await reminderApi.reschedule(before.id, after.remindAt);
    }
    return saved;
  },
  remove: (id: string) => request<void>(`/items/${id}`, { method: 'DELETE' }),
  setStatus: async (id: string, status: Status) => toProduct(await request<ItemOut>(`/items/${id}`, json('PATCH', { status: fromStatus(status) }))),
};

// ---------- リマインド・通知 ----------
export const reminderApi = {
  /** 予定のリマインドを取り消してから、新しい日時を1つ入れます。 */
  async reschedule(itemId: string, remindAt: string): Promise<Product> {
    const { reminders } = await request<{ reminders: { id: string; status: string }[] }>(`/items/${itemId}/reminders`);
    for (const r of reminders.filter(r => r.status === 'scheduled')) await request<void>(`/reminders/${r.id}`, { method: 'DELETE' });
    await request(`/items/${itemId}/reminders`, json('POST', { remindAt, reason: '自分で決めた日時' }));
    return toProduct(await request<ItemOut>(`/items/${itemId}`));
  },
  /** 時刻が来たお知らせ（未回答のもの）。呼んだときに、時刻が来たリマインドがお知らせになります。 */
  async unread(): Promise<NotificationOut[]> {
    const { notifications } = await request<{ notifications: NotificationOut[] }>('/notifications');
    return notifications.filter(n => n.status === 'unread');
  },
  /** お知らせに答えます。「欲しい！」は「あとで」（数日後にまた聞く）として送ります。 */
  async answer(notificationId: string, choice: 'wanted' | 'bought' | 'unneeded'): Promise<Product | null> {
    const answer = choice === 'wanted' ? 'later' : choice === 'bought' ? 'bought' : 'unwanted';
    const res = await request<NotificationOut>(`/notifications/${notificationId}/answer`, json('POST', { answer }));
    return res.item ? toProduct(res.item) : null;
  },
};

// ---------- 生活スタイル ----------
interface LifestyleOut { payday: number; source: 'default' | 'diagnosed' | 'manual'; preferences: Partial<LifestyleProfile> }
export const lifestyleApi = {
  /** 診断がまだなら null。 */
  async get(): Promise<LifestyleProfile | null> {
    const res = await request<LifestyleOut>('/lifestyle');
    if (res.source === 'default') return null;
    const p = res.preferences;
    return {
      payday: p.payday || `${res.payday}日`, favoriteGenres: p.favoriteGenres || [], shoppingStyle: p.shoppingStyle || '',
      budgetTiming: p.budgetTiming || '', reminderTime: p.reminderTime || '',
    };
  },
  async diagnose(profile: LifestyleProfile): Promise<void> {
    const answers = [
      { questionId: 'payday', value: profile.payday },
      { questionId: 'favoriteGenres', value: profile.favoriteGenres.join('、') },
      { questionId: 'shoppingStyle', value: profile.shoppingStyle },
      { questionId: 'budgetTiming', value: profile.budgetTiming },
      { questionId: 'reminderTime', value: profile.reminderTime },
    ];
    await request('/lifestyle/diagnosis', json('POST', { answers }));
  },
};

// ---------- 設定 ----------
export const settingsApi = {
  async get(): Promise<Settings> {
    const s = await request<{ pushEnabled: boolean; privacyMode: boolean }>('/settings');
    return { reminders: s.pushEnabled, hidePrices: s.privacyMode };
  },
  async put(s: Settings): Promise<Settings> {
    const r = await request<{ pushEnabled: boolean; privacyMode: boolean }>('/settings', json('PUT', { pushEnabled: s.reminders, privacyMode: s.hidePrices }));
    return { reminders: r.pushEnabled, hidePrices: r.privacyMode };
  },
};
