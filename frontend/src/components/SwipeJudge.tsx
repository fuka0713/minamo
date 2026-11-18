import { useEffect, useRef, useState } from 'react';
import { ArrowLeft, ArrowRight, Check, Heart, HelpCircle, Trash2 } from 'lucide-react';
import { Empty, Price } from './ui';
import { dateLabel, type Product } from '../domain/types';

type Choice = 'wanted' | 'bought' | 'unneeded';
type Gesture = { x: number; y: number };
const GUIDE_KEY = 'sukushop.v2.judge-guide-seen';

export default function SwipeJudge({ products, hidePrices, onChoose, onOpen }: { products: Product[]; hidePrices: boolean; onChoose: (product: Product, choice: Choice) => void; onOpen: (product: Product) => void }) {
  const [offset, setOffset] = useState(0);
  const [animating, setAnimating] = useState(false);
  const [guideOpen, setGuideOpen] = useState(() => localStorage.getItem(GUIDE_KEY) !== 'true');
  const gesture = useRef<Gesture | null>(null);
  const activeItem = products[0];
  const currentItem = useRef(activeItem);
  const chooseRef = useRef(onChoose);
  currentItem.current = activeItem;
  chooseRef.current = onChoose;

  useEffect(() => {
    const move = (x: number, y: number) => {
      if (!gesture.current) return;
      const dx = x - gesture.current.x;
      const dy = y - gesture.current.y;
      if (Math.abs(dx) > Math.abs(dy) * 1.15) setOffset(dx);
    };
    const finish = (x: number) => {
      const from = gesture.current;
      const item = currentItem.current;
      if (!from || !item) return;
      const dx = x - from.x;
      gesture.current = null;
      if (Math.abs(dx) > 76) {
        const choice: Choice = dx > 0 ? 'wanted' : 'bought';
        setOffset(dx > 0 ? 480 : -480);
        setAnimating(true);
        window.setTimeout(() => {
          chooseRef.current(item, choice);
          setOffset(0);
          setAnimating(false);
        }, 180);
      } else {
        setAnimating(true);
        setOffset(0);
      }
    };
    const mouseMove = (event: MouseEvent) => move(event.clientX, event.clientY);
    const mouseUp = (event: MouseEvent) => finish(event.clientX);
    const touchMove = (event: TouchEvent) => { const touch = event.touches[0]; if (touch) move(touch.clientX, touch.clientY); };
    const touchEnd = (event: TouchEvent) => { const touch = event.changedTouches[0]; if (touch) finish(touch.clientX); };
    const cancel = () => { if (gesture.current) { gesture.current = null; setAnimating(true); setOffset(0); } };
    window.addEventListener('mousemove', mouseMove);
    window.addEventListener('mouseup', mouseUp);
    window.addEventListener('touchmove', touchMove, { passive: true });
    window.addEventListener('touchend', touchEnd);
    window.addEventListener('touchcancel', cancel);
    return () => {
      window.removeEventListener('mousemove', mouseMove);
      window.removeEventListener('mouseup', mouseUp);
      window.removeEventListener('touchmove', touchMove);
      window.removeEventListener('touchend', touchEnd);
      window.removeEventListener('touchcancel', cancel);
    };
  }, []);

  function start(x: number, y: number) {
    if (!activeItem) return;
    gesture.current = { x, y };
    setAnimating(false);
  }
  function closeGuide() {
    setGuideOpen(false);
    localStorage.setItem(GUIDE_KEY, 'true');
  }

  if (!activeItem) return <Empty title="今日はここまで。" description="今日のジャッジはおしまい。次のリマインドまで、ゆっくりしていてね。" />;
  return <section className="judge-stage" aria-label="商品をスワイプしてジャッジ">
    <div className="judge-topline">
      <div className="judge-count"><span>YOUR TURN</span><strong>{products.length}こ</strong><small>今日のジャッジ</small></div>
      <div className="judge-top-actions">
        <button className="gesture-help" onClick={() => setGuideOpen(open => !open)} aria-label="スワイプの使い方"><HelpCircle size={17} /></button>
        <button className="judge-trash" onClick={() => onChoose(activeItem, 'unneeded')} aria-label="もういらないにする"><Trash2 size={17} /></button>
      </div>
    </div>

    {guideOpen && <div className="swipe-tutorial" role="status">
      <div className="tutorial-arrows"><span><ArrowLeft size={16} />買った！</span><i className="tutorial-card">商品カード</i><span>欲しい！<ArrowRight size={16} /></span></div>
      <p>カードを左右に動かして、今の気持ちを教えてください。</p>
      <button onClick={closeGuide}>わかった</button>
    </div>}

    <article className={`judge-card ${animating ? 'is-animating' : ''}`} style={{ transform: `translateX(${offset}px) rotate(${offset / 24}deg)`, touchAction: 'pan-y' }} onMouseDown={event => { if (event.button === 0) start(event.clientX, event.clientY); }} onTouchStart={event => { const touch = event.touches[0]; if (touch) start(touch.clientX, touch.clientY); }}>
      <div className={`swipe-stamp like ${offset > 18 ? 'visible' : ''}`}>欲しい！</div>
      <div className={`swipe-stamp bought ${offset < -18 ? 'visible' : ''}`}>買った！</div>
      <div className={`swipe-tint ${offset > 0 ? 'like' : 'bought'}`} style={{ opacity: Math.min(Math.abs(offset) / 140, .55) }} aria-hidden="true" /><div className="judge-photo"><img src={activeItem.image} alt={activeItem.name} draggable="false" /></div>
      <div className="judge-info"><div className="judge-info-top"><span className="category-label inline-label">{activeItem.category}</span><span className="judge-added">{dateLabel(activeItem.remindAt)} ごろ</span></div><h2>{activeItem.name}</h2>{activeItem.brand && <p className="brand-label">{activeItem.brand}</p>}<Price product={activeItem} hidden={hidePrices} /><button className="text-link" onClick={() => onOpen(activeItem)}>商品詳細を見る<ArrowRight size={14} /></button></div>
    </article>

    <p className="swipe-hint"><ArrowLeft size={15} /><span>左へ：買った！</span><i>·</i><span>右へ：欲しい！</span><ArrowRight size={15} /></p>
    <div className="judge-actions">
      <button className="judge-choice bought-choice" onClick={() => onChoose(activeItem, 'bought')} aria-label="買った"><Check size={22} /><small>買った！</small></button>
      <button className="judge-choice yes" onClick={() => onChoose(activeItem, 'wanted')} aria-label="欲しい"><Heart size={22} /><small>欲しい！</small></button>
    </div>
    {products.length > 1 && <div className="judge-next"><span>このあと</span>{products.slice(1, 4).map(product => <button key={product.id} onClick={() => onOpen(product)}><img src={product.image} alt="" />{product.name}</button>)}</div>}
  </section>;
}
