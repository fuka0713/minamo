/** 猫の部屋の家具。登録したスクショ（商品）の数に応じて増えていく。 */
export const roomItems = [
  { need: 1, id: 'plant', name: 'かんようしょくぶつ' },
  { need: 3, id: 'frame', name: 'かべの絵' },
  { need: 5, id: 'garland', name: 'ガーランド' },
  { need: 8, id: 'lamp', name: 'フロアランプ' },
  { need: 12, id: 'crown', name: '猫のおうかん' },
] as const;
export type RoomItemId = typeof roomItems[number]['id'];
export function roomLevel(count: number) { return roomItems.filter(item => count >= item.need).length; }
export function nextRoomItem(count: number) { return roomItems.find(item => count < item.need) || null; }
