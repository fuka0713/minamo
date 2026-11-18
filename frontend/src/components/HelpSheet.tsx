import { useEffect } from 'react';
import { ArrowLeft, ArrowRight, Bell, Heart, Home as HomeIcon, ImagePlus, Settings, Trash2, X, type LucideIcon } from 'lucide-react';
import type { Page } from '../domain/types';

type Section = { id: Page[]; title: string; icon: LucideIcon; steps: { icon?: LucideIcon; text: string }[] };
const sections: Section[] = [
  { id: ['home'], title: 'ホーム', icon: HomeIcon, steps: [
    { text: '吹き出しには、猫がいま考えている「欲しい」が約5秒ごとに出ます。タップで詳細へ。' },
    { text: 'スクショを登録するほど、猫の部屋に家具が届きます。左下の「おへや Lv.」で次の家具を確認できます。' },
    { text: 'ジャンルのボタンで、下の写真一覧を絞り込めます。' },
  ] },
  { id: ['import', 'results'], title: '写真を追加する', icon: ImagePlus, steps: [
    { text: '下の「＋」からスクショを選ぶと、自動で商品を探します。' },
    { text: '見つかった内容を確認・編集して、「リストに保存」で欲しいものに入ります。' },
  ] },
  { id: ['wishlist', 'detail'], title: '欲しいもの', icon: Heart, steps: [
    { text: '「欲しい／買った／もういらない」で、ジャッジした結果ごとに切り替えられます。' },
    { text: '商品名・ブランドで検索したり、ジャンルで絞り込んだりできます。' },
  ] },
  { id: ['reminders'], title: 'ジャッジ', icon: Heart, steps: [
    { icon: ArrowRight, text: '右へスワイプで「欲しい！」。次のタイミングでまた聞きます。' },
    { icon: ArrowLeft, text: '左へスワイプで「買った！」。' },
    { icon: Trash2, text: '右上のゴミ箱で「もういらない」に整理します。' },
  ] },
  { id: [], title: 'これ買わなくていい？', icon: Bell, steps: [
    { text: '右上のベルから、おすすめの理由つきで「欲しい」を見返せます。' },
    { text: '理由は、お給料日・価格・期間限定・近くのお店などから選ばれます。' },
  ] },
  { id: ['settings', 'diagnosis'], title: '設定', icon: Settings, steps: [
    { text: '「5つの質問を見直す」で生活スタイルを変えると、おすすめの理由やタイミングも変わります。' },
  ] },
];

export default function HelpSheet({ page, onClose }: { page: Page; onClose: () => void }) {
  useEffect(() => { const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); }; window.addEventListener('keydown', esc); return () => window.removeEventListener('keydown', esc); }, [onClose]);
  const current = sections.find(s => s.id.includes(page));
  const ordered = current ? [current, ...sections.filter(s => s !== current)] : sections;
  return <>
    <button className="sheet-backdrop" aria-label="使い方を閉じる" onClick={onClose} />
    <section className="help-sheet" role="dialog" aria-modal="true" aria-label="使い方ガイド">
      <span className="sheet-grip" aria-hidden="true" />
      <header><div><small>HOW TO USE</small><h2>使い方ガイド</h2></div><button aria-label="閉じる" onClick={onClose}><X size={18} /></button></header>
      <div className="help-scroll">{ordered.map(s => { const Icon = s.icon; const here = s === current; return <article key={s.title} className={`help-section ${here ? 'current' : ''}`}>
        <h3><span className="help-icon"><Icon size={16} /></span>{s.title}{here && <em>この画面</em>}</h3>
        <ol>{s.steps.map((step, i) => { const StepIcon = step.icon; return <li key={i}><span className="help-num">{StepIcon ? <StepIcon size={13} /> : i + 1}</span><p>{step.text}</p></li>; })}</ol>
      </article>; })}</div>
    </section>
  </>;
}
