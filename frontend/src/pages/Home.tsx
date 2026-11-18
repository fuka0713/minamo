import { useState } from 'react';
import type { Spotlight } from '../hooks/useSpotlight';
import { ArrowRight, Sparkles } from 'lucide-react';
import { GenreTiles } from '../components/ui';
import RoomDecor from '../components/RoomDecor';
import { nextRoomItem, roomLevel } from '../domain/room';
import { categories, type Page, type Product } from '../domain/types';

export default function Home({ products, navigate, open, hidePrices, notifications, spotlight: { spotlightItems, spotlightIndex, spotlight } }: { spotlight: Spotlight; products: Product[]; navigate: (page: Page) => void; open: (product: Product) => void; hidePrices: boolean; notifications: boolean }) {
  const [genre, setGenre] = useState('すべて');
  const sorted = [...products].sort((a, b) => +new Date(b.createdAt) - +new Date(a.createdAt));
  const genres = categories.filter(c => products.some(p => p.category === c));
  const level = roomLevel(products.length);
  const nextItem = nextRoomItem(products.length);
  const shots = genre === 'すべて' ? sorted : sorted.filter(p => p.category === genre);

  return <>
    <div className="home-intro"><div><p className="eyebrow">YOUR LITTLE WISHES, ALL TOGETHER.</p><h1>欲しい！を、忘れない。</h1><p className="subtitle">スクショから、欲しかったものをまとめよう。</p></div><span className="today-label">{new Date().toLocaleDateString('ja-JP', { month: 'long', day: 'numeric', weekday: 'short' })}</span></div>

    <section className="thought-hero" aria-label="猫が考えている欲しいもの">
      <img className="thought-room" src="/assets/room.webp" alt="本棚のある部屋で、ソファに座って本を読む黒猫" />
      <RoomDecor level={level} />
      <button className="room-badge" onClick={() => navigate('import')} aria-label={nextItem ? `おへやレベル${level}。あと${nextItem.need - products.length}枚で${nextItem.name}が届きます` : `おへやレベル${level}。家具がそろいました`}><b>おへや Lv.{level}</b><span>{nextItem ? <>あと{nextItem.need - products.length}枚で<em>{nextItem.name}</em></> : '家具がそろったよ'}</span></button>
      <button className="thought-bubble" onClick={() => spotlight ? open(spotlight) : navigate('import')} aria-label={spotlight ? `${spotlight.name}の詳細を開く` : '写真を追加する'}>
        <span className="thought-label"><Sparkles size={13} />いま考えているのは…</span>
        {spotlight ? <span className="thought-product" key={spotlight.id}><img src={spotlight.image} alt="" /><span><strong>{spotlight.name}</strong><small>{spotlight.brand || 'まだブランドを確認中'}</small></span><ArrowRight size={16} /></span> : <span className="thought-empty">写真を追加して、猫に教えてあげよう。</span>}
        <span className="thought-caption">タップして商品を見てみる</span>
      </button>
      <span className="thought-dots" aria-label={`${spotlightItems.length}件中${spotlightItems.length ? spotlightIndex % spotlightItems.length + 1 : 0}件目`}>
        {spotlightItems.slice(0, 5).map((product, index) => <i key={product.id} className={index === spotlightIndex % spotlightItems.length ? 'active' : ''} />)}
      </span>
    </section>

    <section className="genre-section"><div className="home-section-head"><h2>ジャンルから探す</h2><button className="text-link" onClick={() => navigate('wishlist')}>すべて見る<ArrowRight size={14} /></button></div>
      <GenreTiles genres={genres} value={genre} onChange={setGenre} />
    </section>

    <section className="shot-section"><div className="home-section-head"><h2>スクショした写真</h2><small>全{shots.length}件</small></div>
      {shots.length ? <div className="shot-grid">{shots.map(product => <button key={product.id} className="shot-card" onClick={() => open(product)}><span className="shot-photo"><img src={product.image} alt={product.name} /></span><span className="shot-body"><strong>{product.name}</strong><small>{new Date(product.createdAt).toLocaleDateString('ja-JP', { month: 'long', day: 'numeric' })}に追加</small></span></button>)}</div> : <div className="soft-panel text-center">気になったものを、ひとつ追加してみよう。<button className="text-link" onClick={() => navigate('import')}>写真を追加</button></div>}
    </section>
  </>;
}
