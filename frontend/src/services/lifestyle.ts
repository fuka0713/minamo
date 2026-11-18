export interface LifestyleProfile {
  payday: string;
  favoriteGenres: string[];
  shoppingStyle: string;
  budgetTiming: string;
  reminderTime: string;
}
const KEY = 'sukushop.v2.lifestyle.v1';
export function loadLifestyle(): LifestyleProfile | null {
  try { const value = localStorage.getItem(KEY); return value ? JSON.parse(value) as LifestyleProfile : null; } catch { return null; }
}
export function saveLifestyle(profile: LifestyleProfile): void { localStorage.setItem(KEY, JSON.stringify(profile)); }
