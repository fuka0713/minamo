import type { AnalysisService } from '../domain/types';
import { itemApi } from './api';

/**
 * 解析：画像をサーバー（POST /api/items）に送ると、OCR（または Gemini）で読み取って登録し、商品が返る。
 * 返ってきた商品には、リマインドの候補日（remindAt）と理由（reminderReason）も入っている。
 */
export const analysisService: AnalysisService = {
  async analyze(screenshot) {
    const blob = await toUploadBlob(screenshot.image);
    return [await itemApi.upload(blob, screenshot.name.replace(/\.\w+$/, '') + '.jpg')];
  },
};

/** 画面で使っている画像（data: URL、またはサンプルの /assets/…svg）を、送れる JPEG にする。 */
async function toUploadBlob(src: string): Promise<Blob> {
  if (src.startsWith('data:image/jpeg')) return (await fetch(src)).blob();
  const img = new Image();
  img.src = src;
  await img.decode();
  const scale = Math.min(1, 1600 / Math.max(img.naturalWidth || 800, img.naturalHeight || 800));
  const canvas = document.createElement('canvas');
  canvas.width = Math.round((img.naturalWidth || 800) * scale); canvas.height = Math.round((img.naturalHeight || 800) * scale);
  const ctx = canvas.getContext('2d')!;
  ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
  return new Promise((resolve, reject) => canvas.toBlob(b => (b ? resolve(b) : reject(new Error('画像を変換できませんでした。'))), 'image/jpeg', 0.85));
}
export async function readScreenshot(file: File): Promise<string> {
  if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) throw new Error(`${file.name}：PNG・JPEG・WebPを選んでください。`);
  if (file.size > 10 * 1024 * 1024) throw new Error(`${file.name}：10MB以下の画像にしてください。`);
  const bitmap = await createImageBitmap(file);
  const scale = Math.min(1, 1600 / Math.max(bitmap.width, bitmap.height)); // 文字を読み取るので、小さくしすぎない
  const canvas = document.createElement('canvas');
  canvas.width = Math.round(bitmap.width * scale); canvas.height = Math.round(bitmap.height * scale);
  const ctx = canvas.getContext('2d')!;
  ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height); bitmap.close();
  return canvas.toDataURL('image/jpeg', .85);
}
