import { ArrowUpRight, Bell, BookOpen, Brush, Coffee, Headphones, Heart, LayoutGrid, Package, Shirt, Sofa, Sparkles, SprayCan, type LucideIcon } from 'lucide-react';
import type { Product } from '../domain/types';
import { dateLabel, safeUrl, statusLabels } from '../domain/types';
export function Mascot({ small = false, className = '' }: { small?: boolean; className?: string }) {
  return <div className={`mascot ${small ? 'mascot-small' : ''} ${className}`}><img src="/assets/cat-portrait.webp" alt="ソファで本を読む、緑の目とネクタイの黒猫" /></div>;
}
export function PageTitle({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: React.ReactNode }) {
  return <div className="page-heading"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p className="subtitle">{description}</p></div>{action}</div>;
}
export function Price({ product, hidden }: { product: Product; hidden?: boolean }) {
  return <span className="price">{hidden ? '••••' : product.price === null ? <span className="unknown-price">価格未確認</span> : new Intl.NumberFormat('ja-JP', { style: 'currency', currency: product.currency || 'JPY' }).format(product.price)}</span>;
}
export function ProductCard({ product: p, onOpen, hidePrices }: { product: Product; onOpen: (p: Product) => void; hidePrices?: boolean }) {
  const overdue = new Date(p.remindAt).getTime() <= Date.now();
  return <article className="product-card"><button className="product-picture" onClick={() => onOpen(p)} aria-label={`${p.name}の詳細`}><img src={p.image} alt={p.name} /><span className="category-label">{p.category}</span><span className="heart-bubble"><Heart size={16} /></span></button><div className="product-body"><p className="brand-label">{p.brand || 'ブランド未確認'}</p><button className="product-name" onClick={() => onOpen(p)}>{p.name}</button><Price product={p} hidden={hidePrices} /><div className="product-date">{new Date(p.createdAt).toLocaleDateString('ja-JP')} に追加 · {statusLabels[p.status]}</div><div className={`product-reminder ${overdue ? 'overdue' : ''}`}><Bell size={13} /><span>{overdue ? 'そろそろ、見直してみる？' : dateLabel(p.remindAt)}</span></div>{safeUrl(p.url) && <a className="shop-link" href={safeUrl(p.url)!} target="_blank" rel="noopener noreferrer">購入先を見る <ArrowUpRight size={13} /></a>}</div></article>;
}
export function Empty({ title, description, action }: { title: string; description: string; action?: React.ReactNode }) {
  return <div className="empty-state"><Mascot small /><h2>{title}</h2><p>{description}</p>{action}</div>;
}
const genreIcons: Record<string, LucideIcon> = { 'すべて': LayoutGrid, 'コスメ': Brush, 'ファッション': Shirt, '家具・インテリア': Sofa, '暮らし': Coffee, '日用品': SprayCan, 'ガジェット': Headphones, '本・文具': BookOpen, 'その他': Package };
export function GenreTiles({ genres, value, onChange }: { genres: string[]; value: string; onChange: (genre: string) => void }) {
  return <div className="genre-tiles" role="group" aria-label="ジャンルで絞り込み">{['すべて', ...genres].map(name => { const Icon = genreIcons[name] || Package; return <button key={name} className={value === name ? 'selected' : ''} onClick={() => onChange(name)} aria-pressed={value === name}><Icon size={22} /><span>{name}</span></button>; })}</div>;
}
