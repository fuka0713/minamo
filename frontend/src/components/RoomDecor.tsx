import type { ReactElement } from 'react';
import { roomItems, type RoomItemId } from '../domain/room';

const S = { stroke: '#3a3a3a', strokeWidth: 3, strokeLinejoin: 'round' as const, strokeLinecap: 'round' as const };
const art: Record<RoomItemId, ReactElement> = {
  plant: <svg viewBox="0 0 80 110"><path d="M40 62C30 40 12 36 6 42c6 14 22 22 34 20z" fill="#8fbf8a" {...S} /><path d="M40 62c8-24 26-30 34-24-4 16-20 24-34 24z" fill="#a9d19a" {...S} /><path d="M40 64C40 36 46 16 40 6c-10 14-8 38 0 58z" fill="#7fb07c" {...S} /><path d="M18 64h44l-6 40H24z" fill="#d9a07a" {...S} /><path d="M16 62h48v9H16z" fill="#c98d68" {...S} /></svg>,
  frame: <svg viewBox="0 0 120 92"><rect x="4" y="4" width="112" height="84" rx="8" fill="#c79a6b" {...S} /><rect x="16" y="16" width="88" height="60" rx="3" fill="#f6efe0" {...S} /><circle cx="80" cy="34" r="8" fill="#f2c86b" /><path d="M18 74l26-30 18 18 12-12 28 24z" fill="#9cc4b8" {...S} strokeWidth={2.5} /></svg>,
  garland: <svg viewBox="0 0 300 50" preserveAspectRatio="none"><path d="M2 6Q150 34 298 6" fill="none" {...S} strokeWidth={2.5} />{[['#f0c9b8', 24], ['#b8d6cf', 66], ['#f2dc9b', 108], ['#c9c3e6', 150], ['#f0c9b8', 192], ['#b8d6cf', 234], ['#f2dc9b', 276]].map(([c, x]) => { const n = Number(x); const y = 6 + 28 * (1 - Math.pow((n - 150) / 148, 2)) * 0.98; return <path key={n} d={`M${n - 11} ${y - 2}L${n + 11} ${y - 2}L${n} ${y + 18}z`} fill={String(c)} {...S} strokeWidth={2.2} />; })}</svg>,
  lamp: <svg viewBox="0 0 70 200"><path d="M35 70v118" {...S} fill="none" strokeWidth={4} /><ellipse cx="35" cy="190" rx="20" ry="6" fill="#8a6e57" {...S} /><path d="M12 70l10-48h26l10 48z" fill="#f4e2b8" {...S} /><ellipse cx="35" cy="74" rx="26" ry="8" fill="#fff4c8" opacity=".75" /></svg>,
  crown: <svg viewBox="0 0 80 56"><path d="M6 48L4 12l20 18L40 4l16 26 20-18-2 36z" fill="#f4cd5c" {...S} /><circle cx="40" cy="30" r="5" fill="#e98b7b" {...S} strokeWidth={2} /><path d="M6 48h68" {...S} /></svg>,
};

export default function RoomDecor({ level }: { level: number }) {
  return <div className="room-decor" aria-hidden="true">{roomItems.slice(0, level).map(item => <span key={item.id} className={`room-item room-${item.id}`}>{art[item.id]}</span>)}</div>;
}
