import { useRef, useState } from 'react';
import { Camera, Check, FolderOpen, ImagePlus, Images, Sparkles, X } from 'lucide-react';
import { PageTitle } from '../components/ui';
import type { LifestyleProfile } from '../services/lifestyle';
import type { Product, Screenshot } from '../domain/types';
import { appIcon } from '../utils/assets';
import { analysisService, readScreenshot } from '../services/analysis';
import { ApiError } from '../services/api';

/** 一度に取りこむ量の上限（たくさん送りすぎないように） */
const LIMITS = { maxFiles: 20, maxBytes: 10 * 1024 * 1024, maxTotalBytes: 100 * 1024 * 1024, types: ['image/png', 'image/jpeg', 'image/webp'] };

export default function ImportPage({ onResults, notify }: { onResults: (products: Product[]) => void; notify: (message: string) => void; profile: LifestyleProfile | null }) {
  const [files, setFiles] = useState<Screenshot[]>([]);
  const [busy, setBusy] = useState(false);
  const [reading, setReading] = useState(false);
  const [completed, setCompleted] = useState(0);
  const multi = useRef<HTMLInputElement>(null);
  const single = useRef<HTMLInputElement>(null);
  const folder = useRef<HTMLInputElement>(null);

  async function runAnalysis(queue: Screenshot[]) {
    if (!queue.length || busy) return;
    setBusy(true);
    setCompleted(0);
    const results: Product[] = [];
    let failed = 0;

    for (let index = 0; index < queue.length; index += 1) {
      const screenshot = queue[index];
      setFiles(current => current.map(file => file.id === screenshot.id ? { ...file, status: 'analyzing' } : file));
      try {
        // サーバーで解析・登録。リマインドの候補日と理由もサーバーが決める
        results.push(...await analysisService.analyze(screenshot));
        setFiles(current => current.map(file => file.id === screenshot.id ? { ...file, status: 'done' } : file));
      } catch (e) {
        failed += 1;
        setFiles(current => current.map(file => file.id === screenshot.id ? { ...file, status: 'error' } : file));
        if (e instanceof ApiError && e.status === 429) { // 送りすぎ：残りは送らずに止める
          notify(e.message);
          const rest = new Set(queue.slice(index + 1).map(file => file.id));
          setFiles(current => current.map(file => rest.has(file.id) ? { ...file, status: 'error' } : file));
          failed += rest.size;
          setCompleted(queue.length);
          break;
        }
      }
      setCompleted(index + 1);
    }

    setBusy(false);
    if (results.length) {
      if (failed) notify(`${results.length}件を解析しました。${failed}枚は解析できなかったため、結果を確認してください。`);
      onResults(results);
    } else {
      notify('解析できませんでした。画像を選び直してください。');
    }
  }

  async function addFiles(list: FileList | null) {
    if (!list || busy || reading) return;
    setReading(true);
    // フォルダごとのときは、画像（PNG・JPEG・WebP）だけを、新しい順に取りこむ。多すぎる・大きすぎる分はとばす
    const all = Array.from(list);
    const images = all.filter(file => LIMITS.types.includes(file.type) && !file.name.startsWith('.')).sort((a, b) => b.lastModified - a.lastModified);
    const notImages = all.length - images.length;
    const added: Screenshot[] = [];
    let tooMany = 0, tooBig = 0, broken = 0, total = 0;
    for (const file of images) {
      if (files.length + added.length >= LIMITS.maxFiles) { tooMany += 1; continue; }
      if (file.size > LIMITS.maxBytes || total + file.size > LIMITS.maxTotalBytes) { tooBig += 1; continue; }
      try {
        const image = await readScreenshot(file); // 長い辺1600pxの JPEG に縮めてから送る
        total += file.size;
        added.push({ id: crypto.randomUUID(), name: file.webkitRelativePath || file.name, image, status: 'ready' });
      } catch {
        broken += 1;
      }
    }
    const queue = [...files, ...added];
    setFiles(queue);
    setReading(false);
    const notes = [
      tooMany && `上限（1回${LIMITS.maxFiles}枚）をこえた${tooMany}枚`,
      tooBig && `大きすぎる（1枚10MB・合計100MBまで）${tooBig}枚`,
      broken && `読みこめなかった${broken}枚`,
      notImages && `画像以外の${notImages}ファイル`,
    ].filter(Boolean);
    if (notes.length) notify(`${added.length}枚を追加しました（新しい順）。${notes.join('・')}は入れていません。`);
    else if (!added.length) notify('追加できる画像がありませんでした（PNG・JPEG・WebP）。');
    if (added.length) void runAnalysis(added); // 新しく選んだ分だけ送る（同じ画像を二重に登録しない）
  }

  function addSampleImages() {
    if (busy || reading) return;
    const samples: Screenshot[] = [
      { id: crypto.randomUUID(), name: 'サンプル画像_コスメ.png', image: '/assets/bag.svg', status: 'ready' },
      { id: crypto.randomUUID(), name: 'サンプル画像_暮らし.png', image: '/assets/mug.svg', status: 'ready' },
      { id: crypto.randomUUID(), name: 'サンプル画像_ガジェット.png', image: '/assets/headphones.svg', status: 'ready' },
    ];
    setFiles(samples);
    void runAnalysis(samples);
  }

  const percent = files.length ? Math.round(completed / files.length * 100) : 0;
  const done = files.filter(file => file.status === 'done').length;

  return <>
    <div className="basket-heading">
      <img src={appIcon} alt="写真入りの買い物かご" />
      <div><PageTitle eyebrow="COLLECT YOUR WISHES" title="スクショを、ひとまとめに。" description="写真に残した「これ欲しい」を、まとめて整理。" /></div>
    </div>
    <div className="flow-steps"><span className="current">1 <b>写真を選ぶ</b></span><i /><span>2 <b>内容を確認</b></span><i /><span>3 <b>リストに保存</b></span></div>

    <input ref={multi} hidden type="file" accept="image/png,image/jpeg,image/webp" multiple onChange={event => { void addFiles(event.target.files); event.target.value = ''; }} />
    <input ref={single} hidden type="file" accept="image/png,image/jpeg,image/webp" onChange={event => { void addFiles(event.target.files); event.target.value = ''; }} />
    <input ref={folder} hidden type="file" multiple {...({ webkitdirectory: '' } as React.InputHTMLAttributes<HTMLInputElement>)} onChange={event => { void addFiles(event.target.files); event.target.value = ''; }} />

    <section className="upload-main">
      <div className="upload-symbol cart-symbol"><img src={appIcon} alt="" /><span>＋</span></div>
      <h2>写真を追加すると、自動で商品を探します。</h2>
      <p>スクショや写真から、欲しかったものをまとめて見つけます。</p>
      <button className="primary" disabled={busy || reading} onClick={() => multi.current?.click()}><ImagePlus size={19} />スクショをまとめて追加</button>
      <small>PNG・JPEG・WebP / 1枚10MBまで / 1回20枚まで（フォルダは新しい順に20枚）</small>
      <div className="upload-alternatives">
        <button disabled={busy || reading} onClick={() => { if (folder.current && 'webkitdirectory' in folder.current) folder.current.click(); else { notify('フォルダ選択に非対応のため、複数ファイル選択を開きます。'); multi.current?.click(); } }}><FolderOpen size={16} />フォルダから追加</button>
        <span />
        <button disabled={busy || reading} onClick={() => single.current?.click()}><Camera size={16} />1枚だけ追加</button>
      </div>
    </section>

    <div className="sample-prompt"><span><Sparkles size={17} />先にサンプルで流れを試せます。</span><button className="text-link" disabled={busy || reading} onClick={addSampleImages}>サンプル画像を追加</button></div>

    {reading && <p role="status" className="soft-panel">画像を読み込んでいます…</p>}
    {files.length > 0 && <>
      <div className="section-heading"><h2>取り込んだ写真 <span>{files.length}枚</span></h2><small>{busy ? 'AI解析中…' : '解析結果を確認しています'}</small></div>
      {busy && <div className="analysis-progress v2-progress" role="status" aria-live="polite">
        <div className="progress-copy"><strong>猫が写真を整理しています</strong><span>{done} / {files.length}枚 · {percent}%</span></div>
        <div className="progress-track" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent}>
          <div className="progress-fill" style={{ width: `${percent}%` }} />
          <img className="progress-cat" src="/assets/cat-head.webp" alt="" style={{ left: `${Math.max(5, Math.min(95, percent))}%` }} />
        </div>
        <p>商品名やジャンルをひとつずつ確認中…</p>
      </div>}
      <div className="preview-grid">{files.map(file => <article className="preview-card" key={file.id}>
        <div className="preview-photo"><img src={file.image} alt={file.name} /><button disabled={busy} onClick={() => setFiles(current => current.filter(item => item.id !== file.id))} className="remove-image" aria-label={`${file.name}を除外`}><X size={16} /></button></div>
        <p>{file.name}</p>
        <small>{file.status === 'done' ? <><Check size={13} />解析できました</> : file.status === 'analyzing' ? '解析中…' : file.status === 'error' ? '解析できませんでした' : '準備中'}</small>
      </article>)}</div>
    </>}
  </>;
}
