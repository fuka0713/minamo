export interface LifestyleProfile {
  payday: string;
  favoriteGenres: string[];
  shoppingStyle: string;
  budgetTiming: string;
  reminderTime: string;
}
const KEY = 'sukushop.v2.lifestyle.v1';
/** 診断の回答の控え（表示用）。本物はサーバー（/api/lifestyle）にある */
export function saveLifestyle(profile: LifestyleProfile): void { localStorage.setItem(KEY, JSON.stringify(profile)); }
