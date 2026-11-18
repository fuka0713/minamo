import { useEffect, useRef, useState } from 'react';
import { HelpCircle, LogOut, Plus, UserRound, ArrowLeft, ArrowRight, Bell, Check, ChevronRight, Clock3, Download, Heart, Home as HomeIcon, ImagePlus, Images, LockKeyhole, Search, Settings as SettingsIcon, ShieldCheck, Sparkles, Trash2, X } from 'lucide-react';
import Home from './pages/Home';
import ImportPage from './pages/Import';
import Detail from './pages/Detail';
import { Empty, GenreTiles, Mascot, PageTitle, Price, ProductCard } from './components/ui';
import Welcome from './pages/Welcome';
import Diagnosis from './pages/Diagnosis';
import SwipeJudge from './components/SwipeJudge';
import HelpSheet from './components/HelpSheet';
import { saveLifestyle, type LifestyleProfile } from './services/lifestyle';
import { categories, dateLabel, isActive, safeUrl, statusLabels, type Page, type Product, type SavedData } from './domain/types';
import { ApiError, authApi, itemApi, lifestyleApi, settingsApi, type User } from './services/api';
import { roomItems, roomLevel } from './domain/room';
import { useSpotlight } from './hooks/useSpotlight';
import { recommendationService } from './services/recommendation';
/** データはサーバー（API）に保存する。起動したときは空で、ログインのあとに読み込む。 */
const initial = (): { data: SavedData; error: boolean } => ({ data: { version: 1, products: [], settings: { reminders: true, hidePrices: false } }, error: false });
/** 画面に出す名前：ゲストは「ゲスト」、みんなのデモは「test（みんなのデモ）」 */
const displayName = (u: User | null) => !u ? '' : u.username.endsWith('@guest.invalid') ? 'ゲスト' : u.username === 'test@demo.invalid' ? 'test（みんなのデモ）' : u.username;
const errorText = (e: unknown) => (e instanceof Error ? e.message : '通信でエラーが起きました。');
/** サーバーに送る必要がある違いがあるか（画面だけの項目は比べない） */
const sameProduct = (a: Product, b: Product) => (['name', 'brand', 'category', 'price', 'currency', 'shop', 'url', 'description', 'repeat', 'status', 'remindAt'] as const).every(k => a[k] === b[k]);
const pages: Page[] = ['account','diagnosis','home','import','results','wishlist','detail','reminders','settings'];
const fromHash = () => { const p = location.hash.slice(1) as Page; return pages.includes(p) ? p : 'home'; };
export default function App() {
  const [loaded] = useState(initial), [data, setData] = useState(loaded.data);
  const [journey, setJourney] = useState({ signedIn: false, diagnosed: false });
  const journeyRef = useRef(journey); journeyRef.current = journey; // ページ切り替え（#ハッシュ）で、いちばん新しい状態を見るため
  const [page, setPage] = useState<Page>('account');
  const [booting, setBooting] = useState(true); // 起動したとき：ログイン済みかを確かめている間
  const [user, setUser] = useState<User | null>(null); // ログインしている人
  const [diagnosisReturn, setDiagnosisReturn] = useState<Page>('home');
  const [profile, setProfile] = useState<LifestyleProfile | null>(null);
  const [selected, setSelected] = useState<Product | null>(null), [drafts, setDrafts] = useState<Product[]>([]), [editingDraft, setEditingDraft] = useState(false);
  const [query, setQuery] = useState(''), [category, setCategory] = useState('すべて'), [status, setStatus] = useState('active'), [sort, setSort] = useState('new');
  const [message, setMessage] = useState(''), [undo, setUndo] = useState<Product | null>(null), [clock, setClock] = useState(Date.now()), [days, setDays] = useState(0);
  const notify = (s: string) => setMessage(s);
  const spot = useSpotlight(data.products);
  const [helpOpen, setHelpOpen] = useState(false), [helpSeen, setHelpSeen] = useState(() => { try { return localStorage.getItem('sukushop.v2.help-seen') === 'true'; } catch { return true; } });
  const [notifOpen, setNotifOpen] = useState(false), [notifSeen, setNotifSeen] = useState(false);
  // ---- サーバー（API）との同期 ----
  const server = useRef(new Map<string, Product>()); // サーバーにある、いちばん新しい状態（商品ごと）
  const pendingDeletes = useRef(new Map<string, number>()); // 削除の待ち（「元に戻す」に間に合うよう、少し待ってから消す）
  const dataRef = useRef(data); dataRef.current = data;
  /** ログインのあと：商品・設定・生活スタイルを読み込む。診断がまだなら null を返す。 */
  async function loadAll() {
    const [items, settings, life] = await Promise.all([itemApi.listAll(), settingsApi.get(), lifestyleApi.get()]);
    server.current = new Map(items.map(p => [p.id, p]));
    setData({ version: 1, products: items, settings });
    setProfile(life);
    if (life) saveLifestyle(life); else localStorage.removeItem('sukushop.v2.lifestyle.v1');
    return life;
  }
  async function afterLogin() {
    setUser(await authApi.me());
    const life = await loadAll();
    journeyRef.current = { signedIn: true, diagnosed: Boolean(life) };
    setJourney(journeyRef.current);
    setDiagnosisReturn('home');
    navigate(life ? (fromHash() === 'account' ? 'home' : fromHash()) : 'diagnosis');
  }
  useEffect(() => { (async () => { try { await afterLogin(); } catch (e) { if (!(e instanceof ApiError && e.status === 401)) setMessage(errorText(e)); setPage('account'); } finally { setBooting(false); } })(); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  function deleteNow(id: string) {
    window.clearTimeout(pendingDeletes.current.get(id)); pendingDeletes.current.delete(id);
    if (dataRef.current.products.some(p => p.id === id)) return; // 元に戻された
    server.current.delete(id);
    itemApi.remove(id).catch(e => notify(errorText(e)));
  }
  /** 画面の変更を、サーバーに送る（送った項目だけ。削除は少し待つ） */
  async function sync(prev: SavedData, next: SavedData) {
    try {
      if (prev.settings.reminders !== next.settings.reminders || prev.settings.hidePrices !== next.settings.hidePrices) await settingsApi.put(next.settings);
      const ids = new Set(next.products.map(p => p.id));
      for (const p of prev.products) if (!ids.has(p.id) && !pendingDeletes.current.has(p.id)) pendingDeletes.current.set(p.id, window.setTimeout(() => deleteNow(p.id), 60000));
      for (const p of next.products) {
        if (pendingDeletes.current.has(p.id)) { window.clearTimeout(pendingDeletes.current.get(p.id)); pendingDeletes.current.delete(p.id); } // 「元に戻す」
        const base = server.current.get(p.id);
        if (!base) { setData(d => ({ ...d, products: d.products.filter(x => x.id !== p.id) })); notify('この商品はもう削除されていたため、元に戻せませんでした。'); continue; }
        if (sameProduct(base, p)) continue;
        const saved = await itemApi.save(base, p);
        server.current.set(saved.id, saved);
        setData(d => ({ ...d, products: d.products.map(x => x.id === saved.id ? saved : x) }));
      }
    } catch (e) { notify(errorText(e)); }
  }
  useEffect(() => { const onHash = () => { const next = fromHash(), j = journeyRef.current; setPage(!j.signedIn ? 'account' : !j.diagnosed && next !== 'diagnosis' ? 'diagnosis' : next); window.scrollTo(0,0); }; window.addEventListener('hashchange', onHash); return () => window.removeEventListener('hashchange', onHash); }, []);
  useEffect(() => { if (!message) return; const t = setTimeout(() => setMessage(''), 5500); return () => clearTimeout(t); }, [message]);
  useEffect(() => { const t = setInterval(() => setClock(Date.now()), 30000); return () => clearInterval(t); }, []);
  const navigate = (p: Page) => { setNotifOpen(false); setHelpOpen(false); setPage(p); location.hash = p; window.scrollTo(0,0); };
  const persist = (next: SavedData) => { if (loaded.error) { notify('保存データの読み込みに失敗したため、上書きを停止しています。'); return false; } const prev = data; setData(next); void sync(prev, next); return true; }; // 画面はすぐ変え、サーバーには後ろで送る
  const open = (p: Product) => { setSelected(p); setEditingDraft(false); navigate('detail'); };
  const update = (p: Product) => { if (persist({ ...data, products: data.products.map(x => x.id === p.id ? p : x) })) notify('変更を保存しました。'); };
  const now = clock + days * 86400000;
  const due = data.products.filter(p => isActive(p) && +new Date(p.remindAt) <= now);
  const nav = [{ id: 'home' as const, label: 'ホーム', icon: HomeIcon }, { id: 'wishlist' as const, label: '欲しいもの', icon: Heart }, { id: 'import' as const, label: '追加', icon: Plus }, { id: 'reminders' as const, label: 'ジャッジ', icon: Bell }, { id: 'settings' as const, label: '設定', icon: SettingsIcon }];
  const filtered = data.products.filter(p => (status === 'active' ? isActive(p) : status === 'all' || p.status === status) && (category === 'すべて' || p.category === category) && `${p.name} ${p.brand || ''} ${p.description}`.toLowerCase().includes(query.toLowerCase())).sort((a,b) => sort === 'price' ? (a.price ?? Infinity) - (b.price ?? Infinity) : sort === 'reminder' ? +new Date(a.remindAt) - +new Date(b.remindAt) : +new Date(b.createdAt) - +new Date(a.createdAt));
  function decide(p: Product, choice: 'wanted' | 'hold' | 'bought' | 'unneeded') {
    let next = { ...p, status: choice };
    if (choice === 'wanted' || choice === 'hold') {
      const d = new Date(now);
      if (choice === 'hold') d.setDate(d.getDate()+1);
      else if (p.repeat === 'monthly') { const day = d.getDate(); d.setDate(1); d.setMonth(d.getMonth()+1); d.setDate(Math.min(day,new Date(d.getFullYear(),d.getMonth()+1,0).getDate())); }
      else d.setDate(d.getDate() + (p.repeat === 'daily' ? 1 : p.repeat === 'weekly' ? 7 : 3));
      next = { ...next, remindAt: d.toISOString() };
    }
    update(next);
  }
  async function logout() { await authApi.logout().catch(() => undefined); localStorage.removeItem('sukushop.v2.lifestyle.v1'); server.current.clear(); setData(initial().data); setProfile(null); setUser(null); setJourney({ signedIn: false, diagnosed: false }); navigate('account'); }
  function exportData() { const url = URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{ type: 'application/json' })); const a = document.createElement('a'); a.href = url; a.download = 'sukushop-data.json'; a.click(); setTimeout(() => URL.revokeObjectURL(url),1000); notify('データを書き出しました。画像・価格も含まれます。'); }
  if (booting) return <div className="app-layout" />;
  if (page === 'account' || !journey.signedIn) return <div className="app-layout"><Welcome onContinue={afterLogin} />{message && <div className="toast" role="status">{message}</div>}</div>;
  if (page === 'diagnosis') return <div className="app-layout"><Diagnosis initial={profile} editing={journey.diagnosed} onBack={() => { if (journey.diagnosed) navigate(diagnosisReturn); else navigate('account'); }} onComplete={value => { lifestyleApi.diagnose(value).catch(e => notify(errorText(e))); saveLifestyle(value); setProfile(value); setJourney(j => ({ ...j, signedIn: true, diagnosed: true })); navigate(diagnosisReturn); notify(diagnosisReturn === 'settings' ? '生活スタイルを更新しました。' : '診断できました。ホームへようこそ！'); }} /></div>;
  return <div className="app-layout"><aside className="sidebar"><button className="wordmark" onClick={() => navigate('home')}><img src="/assets/app-icon.png" alt="写真入りショッピングカート" /><span><img className="wordmark-logo" src="/assets/logo.png" alt="すくしょっぷ" /><small>SCREENSHOT TO WISHLIST</small></span></button><div className="sidebar-caption">欲しい気持ちの、置き場所。</div><nav aria-label="メインメニュー">{nav.map(({id,label,icon: Icon}) => <button key={id} className={`nav-item ${id === 'import' ? 'nav-add' : ''} ${page === id || (id === 'import' && page === 'results') || (id === 'wishlist' && page === 'detail') ? 'active' : ''}`} onClick={() => navigate(id)}><Icon size={20} /><span>{label}</span>{id === 'reminders' && due.length > 0 && <b>{due.length}</b>}</button>)}</nav><div className="sidebar-footer"><div className="sidebar-tip"><Heart size={22} /><p>写真に埋もれた「欲しい」を、<br />いっしょに見つけよう。</p><small>スクショも、思い出も、ここに整理。</small></div><span><ShieldCheck size={14} />データはあなたのアカウントに保存</span></div></aside><div className="main-shell"><header className="topbar"><span className="desktop-crumb">わたしのすくしょっぷ <ChevronRight size={12} />{page === 'results' ? '解析結果' : page === 'detail' ? '商品詳細' : nav.find(n => n.id === page)?.label}</span><button className="mobile-wordmark" onClick={() => navigate('home')}><img src="/assets/app-icon.png" alt="" /><img className="wordmark-logo" src="/assets/logo.png" alt="すくしょっぷ" /></button><div className="topbar-right"><span className="demo-tag">UI DEMO</span><button aria-label="使い方ガイドを開く" className={`header-icon help-btn ${helpSeen ? "" : "unseen"}`} onClick={() => { setNotifOpen(false); setHelpOpen(true); if (!helpSeen) { setHelpSeen(true); try { localStorage.setItem("sukushop.v2.help-seen", "true"); } catch { /* ignore */ } } }}><HelpCircle size={20} /></button><button aria-label="「これ買わなくていい？」を開く" aria-expanded={notifOpen} className={`header-icon ${notifOpen ? 'open' : ''}`} onClick={() => { setNotifOpen(o => !o); setNotifSeen(true); }}><Bell size={20} />{spot.spotlight && data.settings.reminders && !notifSeen && <i />}</button>{notifOpen && <><button className="notif-backdrop" aria-label="「これ買わなくていい？」を閉じる" onClick={() => setNotifOpen(false)} /><section className="notif-panel" role="dialog" aria-label="これ買わなくていい？"><header><strong>これ買わなくていい？</strong>{data.settings.reminders && spot.spotlightItems.length > 0 && <span className="notif-count">{spot.spotlightItems.length}件</span>}<button aria-label="閉じる" onClick={() => setNotifOpen(false)}><X size={18} /></button></header>{spot.spotlightItems.length && data.settings.reminders ? <ul className="notif-list">{spot.spotlightItems.map(p => { const rec = recommendationService.recommend(p, profile), current = spot.spotlight?.id === p.id; return <li key={p.id}><button className={`notif-card ${current ? 'current' : ''}`} onClick={() => { setNotifOpen(false); open(p); }}><img src={p.image} alt="" /><span className="notif-body">{current && <small><Sparkles size={12} />いま考えているのは…</small>}<strong>{p.name}</strong><span className="notif-reason"><b>おすすめの理由</b>{rec.reason}</span></span><ChevronRight size={18} /></button></li>; })}</ul> : <p className="notif-empty">{data.settings.reminders ? 'いまはお知らせはありません。' : 'アプリ内のリマインドはオフになっています。'}</p>}{due.length > 0 && <button className="notif-judge" onClick={() => { setNotifOpen(false); navigate('reminders'); }}><Bell size={15} />今日のジャッジが{due.length}こあります<ChevronRight size={15} /></button>}</section></>}<button className="user-avatar" aria-label="設定を開く" onClick={() => navigate('settings')}>{displayName(user).slice(0, 1).toUpperCase() || 'S'}</button></div></header><main>
  {loaded.error && <p role="alert" className="error-text">保存データを読み込めませんでした。既存データ保護のため保存を停止しています。</p>}
  {page === 'home' && <Home spotlight={spot} products={data.products} navigate={navigate} open={open} hidePrices={data.settings.hidePrices} notifications={data.settings.reminders} />}
  {page === 'import' && <ImportPage profile={profile} notify={notify} onResults={p => { p.forEach(x => server.current.set(x.id, x)); setDrafts(p); navigate('results'); }} />}
  {page === 'results' && <><PageTitle eyebrow="A FEW THINGS WE FOUND" title="見つけた「欲しい」を確認しよう。" description="名前や価格が違っていたら、登録前に編集できます。" /><div className="flow-steps"><span>1 <b>スクショを選ぶ</b></span><i /><span className="current">2 <b>内容を確認する</b></span><i /><span>3 <b>リストに保存</b></span></div>{drafts.length ? <><div className="result-summary"><Check size={21} /><strong>{drafts.length}この商品候補があります</strong><span>{categories.filter(c => drafts.some(p => p.category === c)).map(c => `${c} ${drafts.filter(p => p.category === c).length}こ`).join('・')}</span></div><div className="results-list">{[...drafts].sort((a, b) => categories.indexOf(a.category) - categories.indexOf(b.category)).map(p => <article className="result-card" key={p.id}><img src={p.image} alt={p.name} /><div><span className="category-label inline-label">{p.category}</span>{p.identification !== 'identified' && <span className="warning-tag">商品未特定 · 要確認</span>}<h3>{p.name}</h3><p>ブランド：{p.brand || '未確認'}　/　販売元：{p.shop || '未確認'}</p><p className="suggestion-reason">リマインド候補：{dateLabel(p.remindAt)} · {p.reminderReason || 'あとで見直す候補日です。'}</p><Price product={p} hidden={data.settings.hidePrices} /><small>自動で読み取った結果です。内容を確認してから登録してください。</small></div><div className="result-actions"><button className="secondary" onClick={() => { setSelected(p); setEditingDraft(true); navigate('detail'); }}>内容を編集</button><button className="text-link muted" onClick={() => { setDrafts(old => old.filter(x => x.id !== p.id)); server.current.delete(p.id); itemApi.remove(p.id).catch(e => notify(errorText(e))); }}><X size={15} />除外</button></div></article>)}</div><div className="result-footer"><button className="secondary" onClick={() => navigate('import')}><ArrowLeft size={16} />取り込みに戻る</button><button className="primary" onClick={() => { const before = roomLevel(data.products.length), after = roomLevel(data.products.length + drafts.length); if (persist({ ...data, products: [...drafts, ...data.products] })) { setDrafts([]); navigate('wishlist'); notify(after > before ? `保存しました。猫の部屋に「${roomItems[after - 1].name}」が届いたよ！` : '欲しいものリストに保存しました。'); } }}><Heart size={17} />{drafts.length}こをリストに保存</button></div></> : <Empty title="確認する商品はまだありません。" description="スクショを追加すると、自動で解析が始まります。" action={<button className="primary" onClick={() => navigate('import')}>スクショを追加する</button>} />}</>}
  {page === 'wishlist' && <><PageTitle eyebrow="MY WISHLIST" title="わたしの、欲しいもの。" description="好きなものも、迷っているものも。ここでゆっくり整理しよう。" /><div className="list-toolbar"><label className="search-box"><Search size={18} /><input type="search" aria-label="キーワード検索" placeholder="商品名・ブランドで検索" value={query} onChange={e => setQuery(e.target.value)} /></label><div className="status-seg" role="tablist" aria-label="状態で絞り込み">{([["active", "欲しい", Heart], ["bought", "買った", Check], ["unneeded", "もういらない", Trash2], ["all", "すべて", null]] as const).map(([v, l, Icon]) => <button key={v} role="tab" aria-selected={status === v} className={`${status === v ? "selected" : ""} seg-${v}`} onClick={() => setStatus(v)}>{Icon && <Icon size={15} />}{l}<b>{v === "active" ? data.products.filter(isActive).length : v === "all" ? data.products.length : data.products.filter(p => p.status === v).length}</b></button>)}</div><select aria-label="並び替え" value={sort} onChange={e => setSort(e.target.value)}><option value="new">追加した順</option><option value="price">価格が安い順</option><option value="reminder">リマインド順</option></select></div><div className="wishlist-genres"><GenreTiles genres={categories} value={category} onChange={setCategory} /><span className="wishlist-count">{filtered.length}このアイテム</span></div>{filtered.length ? <div className="product-grid">{filtered.map(p => <ProductCard key={p.id} product={p} onOpen={open} hidePrices={data.settings.hidePrices} />)}</div> : <Empty title="ここには、まだ何もないみたい。" description="検索条件を変えるか、新しいスクショを追加してね。" action={<button className="secondary" onClick={() => { setQuery(''); setCategory('すべて'); setStatus('all'); }}>絞り込みを解除</button>} />}</>}
  {page === 'detail' && (selected ? <Detail key={selected.id} product={selected} isDraft={editingDraft} onBack={() => navigate(editingDraft ? 'results' : 'wishlist')} onSave={p => { if (editingDraft) { setDrafts(old => old.map(x => x.id === p.id ? p : x)); navigate('results'); } else if (persist({ ...data, products: data.products.map(x => x.id === p.id ? p : x) })) { navigate('wishlist'); notify('変更を保存しました。'); } }} onDelete={editingDraft ? undefined : () => { if (persist({ ...data, products: data.products.filter(x => x.id !== selected.id) })) { setUndo(selected); navigate('wishlist'); notify('商品を削除しました。下のボタンで元に戻せます。'); } }} /> : <Empty title="商品を選んでください。" description="欲しいものリストから詳細を開けます。" action={<button className="primary" onClick={() => navigate('wishlist')}>リストへ</button>} />)}
  {page === 'reminders' && <><PageTitle eyebrow="A MOMENT TO DECIDE" title="ジャッジ" description="左へスワイプで「買った！」、右へスワイプで「欲しい！」。不要なものは右上のゴミ箱へ。" /><div className="demo-clock"><span><Clock3 size={16} />{days ? `デモ時刻（${days}日後）` : '現在'}：{dateLabel(new Date(now).toISOString())}</span><button className="secondary" onClick={() => setDays(d => d+1)}>1日進めて体験</button>{days > 0 && <button className="text-link" onClick={() => setDays(0)}>現在に戻す</button>}</div><SwipeJudge products={[...due].sort((a,b) => +new Date(a.remindAt)-+new Date(b.remindAt))} hidePrices={data.settings.hidePrices} onOpen={open} onChoose={(p,choice) => { decide(p,choice); notify(choice === 'wanted' ? '「欲しい！」にしました。次のタイミングでまた聞きます。' : choice === 'bought' ? '「買った！」にしました。' : '「もういらない」に整理しました。'); }} /><p className="privacy-note">右へスワイプ＝欲しい！ · 左へスワイプ＝買った！ · ゴミ箱＝もういらない</p></>}
  {page === 'settings' && <><PageTitle eyebrow="JUST THE WAY YOU LIKE" title="わたしに合う、使い方。" description="通知も、データも。安心して使うための設定です。" /><div className="settings-layout"><section className="panel"><h2><UserRound size={19} />アカウント</h2><p className="field-note">ログイン中：{displayName(user)}{user?.username.endsWith('@guest.invalid') ? '（ログアウトすると、このゲストには戻れません）' : ''}</p><button className="secondary" onClick={() => void logout()}><LogOut size={16} />ログアウト</button></section><section className="panel"><h2><Sparkles size={19} />生活スタイル</h2><p className="field-note">{profile ? `給料日：${profile.payday} · よく見るジャンル：${profile.favoriteGenres.join("・") || "未選択"}` : "診断の回答はまだありません。"}</p><button className="secondary" onClick={() => { setDiagnosisReturn('settings'); navigate('diagnosis'); }}>5つの質問を見直す</button></section><section className="panel"><h2><Bell size={19} />お知らせ</h2><label className="toggle-row"><span><strong>アプリ内のリマインド</strong><small>ホーム画面に、見直すタイミングをお知らせ。</small></span><input type="checkbox" role="switch" checked={data.settings.reminders} onChange={e => persist({ ...data, settings: { ...data.settings, reminders: e.target.checked } })} /></label><p className="field-note">アプリを開いたときに確認できます。閉じている間の通知は未対応です。</p></section><section className="panel"><h2><Download size={19} />データ管理</h2><p className="field-note">保存済み：{data.products.length}こ。JSONには画像・価格も含まれます。</p><button className="secondary" onClick={exportData}><Download size={16} />データを書き出す</button><p className="field-note">再インポート・クラウド同期は今後の実装です。</p></section></div></>}
  <footer className="footer"><span>すくしょっぷ <small>スクショから、欲しいを整理。</small></span><span><LockKeyhole size={12} /> スマホの写真から、欲しいものを見つけて整理。</span></footer>
  </main></div>{undo && <div className="undo-bar"><span>「{undo.name}」を削除しました</span><button onClick={() => { if (persist({ ...data, products: [undo,...data.products] })) { setUndo(null); notify('元に戻しました。'); } }}>元に戻す</button><button aria-label="削除の取り消し案内を閉じる" onClick={() => { deleteNow(undo.id); setUndo(null); }}><X size={16} /></button></div>}{message && <div className="toast" role="status">{message}</div>}{helpOpen && <HelpSheet page={page} onClose={() => setHelpOpen(false)} />}</div>;
}
