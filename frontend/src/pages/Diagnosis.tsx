import { useState } from 'react';
import { ArrowLeft, ArrowRight, Check, Sparkles } from 'lucide-react';
import type { LifestyleProfile } from '../services/lifestyle';

const defaults: LifestyleProfile = { payday: '25日', favoriteGenres: [], shoppingStyle: 'ネットで見ることが多い', budgetTiming: '給料日のあと', reminderTime: '夜（18〜22時）' };
const questions = [
  { title: 'お給料日はいつごろ？', hint: 'お買いものを考えるタイミングの参考にします。', kind: 'single', options: ['1日', '5日', '10日', '15日', '20日', '25日', '月末', '決まっていない'] },
  { title: 'よく見るジャンルは？', hint: '複数選べます。後から変更できます。', kind: 'multiple', options: ['ファッション', 'コスメ', '暮らし', 'ガジェット', '本・文具', 'その他'] },
  { title: 'お買いものはどんなスタイル？', hint: '思い出すきっかけを考えるための質問です。', kind: 'single', options: ['ネットで見ることが多い', 'お店で見ることが多い', 'どちらも同じくらい'] },
  { title: '買うものを考えることが多いのは？', hint: '無理のないタイミングを一緒に探します。', kind: 'single', options: ['給料日のあと', '月の真ん中', '月末ごろ', '特に決まっていない'] },
  { title: 'お知らせを見るならいつがいい？', hint: 'お知らせを届けるタイミングに使います。', kind: 'single', options: ['朝（6〜11時）', '昼（11〜18時）', '夜（18〜22時）'] },
] as const;
export default function Diagnosis({ initial, editing, onBack, onComplete }: { initial: LifestyleProfile | null; editing: boolean; onBack: () => void; onComplete: (profile: LifestyleProfile) => void }) {
  const [step, setStep] = useState(0);
  const [profile, setProfile] = useState<LifestyleProfile>(initial || defaults);
  const q = questions[step];
  const singleValue = [profile.payday, profile.shoppingStyle, profile.budgetTiming, profile.reminderTime][step === 0 ? 0 : step === 2 ? 1 : step === 3 ? 2 : 3];
  function choose(value: string) {
    if (step === 1) setProfile(p => ({ ...p, favoriteGenres: p.favoriteGenres.includes(value) ? p.favoriteGenres.filter(x => x !== value) : [...p.favoriteGenres, value] }));
    else if (step === 0) setProfile(p => ({ ...p, payday: value }));
    else if (step === 2) setProfile(p => ({ ...p, shoppingStyle: value }));
    else if (step === 3) setProfile(p => ({ ...p, budgetTiming: value }));
    else setProfile(p => ({ ...p, reminderTime: value }));
  }
  return <main className="diagnosis-screen"><section className="diagnosis-card">
    <button className="text-link diagnosis-back" onClick={onBack}><ArrowLeft size={16} />{editing ? '設定に戻る' : 'ログイン画面に戻る'}</button>
    <img className="diagnosis-cat" src="/assets/cat-portrait.webp" alt="ソファで本を読む黒猫" />
    <p className="eyebrow">A LITTLE ABOUT YOUR ROUTINE</p>
    <h1>{editing ? '生活スタイルを見直そう。' : 'あなたのことを、少しだけ。'}</h1>
    <p className="welcome-lead">{editing ? '回答はいつでも変更できます。' : '5つの質問から、思い出すタイミングを考えます。'}</p>
    <div className="diagnosis-progress"><span>QUESTION {step + 1} / 5</span><div><i style={{ width: `${(step + 1) * 20}%` }} /></div></div>
    <span className="diagnosis-number">0{step + 1}</span><h2>{q.title}</h2><p className="diagnosis-hint">{q.hint}</p>
    <div className={`answer-options ${q.kind === 'multiple' ? 'multiple' : ''}`}>{q.options.map(option => {
      const selected = step === 1 ? profile.favoriteGenres.includes(option) : option === singleValue;
      return <button key={option} className={selected ? 'selected' : ''} onClick={() => choose(option)}>{option}{selected && <Check size={17} />}</button>;
    })}</div>
    <div className="diagnosis-actions">{step > 0 && <button className="secondary" onClick={() => setStep(n => n - 1)}><ArrowLeft size={16} />戻る</button>}{step < 4 ? <button className="primary" onClick={() => setStep(n => n + 1)}>次へ<ArrowRight size={16} /></button> : <button className="primary" onClick={() => onComplete(profile)}><Sparkles size={17} />{editing ? '回答を保存' : 'ホームへ進む'}</button>}</div>
  </section></main>;
}
