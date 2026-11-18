import { useEffect, useState } from 'react';
import { isActive, type Product } from '../domain/types';

/** 「いま考えているのは…」で約5秒ごとに切り替わる商品。ホームの吹き出しと通知で同じものを使う。 */
export function useSpotlight(products: Product[]) {
  const recent = [...products].sort((a, b) => +new Date(b.createdAt) - +new Date(a.createdAt)).slice(0, 4);
  const active = products.filter(isActive);
  const spotlightItems = active.length ? active : recent;
  const [spotlightIndex, setSpotlightIndex] = useState(0);
  const spotlight = spotlightItems.length ? spotlightItems[spotlightIndex % spotlightItems.length] : null;

  useEffect(() => {
    if (spotlightItems.length < 2) return;
    const timer = window.setInterval(() => setSpotlightIndex(index => (index + 1) % spotlightItems.length), 5200);
    return () => window.clearInterval(timer);
  }, [spotlightItems.length]);

  return { spotlightItems, spotlightIndex, spotlight };
}
export type Spotlight = ReturnType<typeof useSpotlight>;
