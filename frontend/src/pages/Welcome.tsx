import { useState } from 'react';
import { ArrowRight, LockKeyhole, Mail, Sparkles } from 'lucide-react';
import { authService } from '../services/auth';
import { appIcon } from '../utils/assets';

export default function Welcome({ onContinue }: { onContinue: () => void | Promise<void> }) {
  const [mode, setMode] = useState<'login' | 'signup'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function submit(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setError('');
    try { await (mode === 'login' ? authService.signIn(email, password) : authService.signUp(email, password)); await onContinue(); }
    catch (err) { setError(err instanceof Error ? err.message : 'ログインできませんでした。'); }
    finally { setBusy(false); }
  }
  return <main className="welcome-screen"><section className="welcome-card">
    <img className="welcome-icon" src={appIcon} alt="写真が入ったショッピングカート" />
    <p className="eyebrow">YOUR WISHES, REMEMBERED.</p>
    <h1>{mode === 'login' ? 'おかえりなさい。' : 'はじめまして。'}</h1>
    <p className="welcome-lead">スクショに残した「欲しい」を、<br />あとから見つけやすく。</p>
    <div className="auth-switch"><button className={mode === 'login' ? 'active' : ''} onClick={() => setMode('login')}>ログイン</button><button className={mode === 'signup' ? 'active' : ''} onClick={() => setMode('signup')}>新規登録</button></div>
    <form onSubmit={submit}>
      <label className="welcome-field"><span><Mail size={16} />メールアドレス</span><input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="hello@example.com" autoComplete="email" /></label>
      <label className="welcome-field"><span><LockKeyhole size={16} />パスワード</span><input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="8文字以上" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} /></label>
      {error && <p role="alert" className="error-text">{error}</p>}
      <button className="primary welcome-submit" disabled={busy}>{mode === 'login' ? 'ログインしてはじめる' : 'アカウントを作ってはじめる'}<ArrowRight size={17} /></button>
    </form>
    <div className="demo-login"><Sparkles size={15} /><span>デモでは入力なしでも先へ進めます（ゲストとして入り、このブラウザだけで使えます）。</span></div>
  </section></main>;
}
