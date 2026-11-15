// analyze.ts のテスト（npm test で実行）
import { test } from "node:test";
import assert from "node:assert/strict";
import { findGenre, findPrice, findTitle, findUrl } from "./analyze.js";

test("価格を読み取る", () => {
  assert.equal(findPrice("税込 3,980円"), 3980);
  assert.equal(findPrice("¥1,200"), 1200);
  assert.equal(findPrice("２，５００円"), 2500); // 全角
  assert.equal(findPrice("価格未定"), null);
});

test("URL を読み取る", () => {
  assert.equal(findUrl("詳細は https://example.com/item/1 へ"), "https://example.com/item/1");
  assert.equal(findUrl("URL なし"), null);
});

test("時刻や価格だけの行は商品名にしない", () => {
  assert.equal(findTitle("12:34\n80%\n¥3,980\nふわふわニットカーディガン"), "ふわふわニットカーディガン");
  assert.equal(findTitle("12:34\n¥3,980"), null);
});

test("キーワードでジャンルを分ける", () => {
  assert.equal(findGenre("限定コラボ ぬいぐるみ 受注開始"), "goods");
  assert.equal(findGenre("ワイヤレスイヤホン Bluetooth"), "gadget");
  assert.equal(findGenre("ウォータリーティント リップ"), "cosme");
  assert.equal(findGenre("醤油ラーメン 営業時間 11:00"), "food");
  assert.equal(findGenre("今日は晴れ"), "other");
});

// ---- 期間の読み取り（今日を 2026/11/14 として試す） ----
import { findPeriod } from "./analyze.js";
const today = new Date(2026, 10, 14);

test("コラボの開催期間を読み取る", () => {
  const p = findPeriod("ちいかわ×〇〇カフェ\n開催期間 11/1(金)〜11/30(土)", today);
  assert.equal(p.start, "2026-11-01");
  assert.equal(p.end, "2026-11-30");
});

test("年・月・日の書き方や全角でも読み取る", () => {
  const p = findPeriod("２０２６年１２月１日～２０２６年１２月２５日", today);
  assert.equal(p.start, "2026-12-01");
  assert.equal(p.end, "2026-12-25");
});

test("終わりが日だけでも読み取る", () => {
  const p = findPeriod("12/1〜25日", today);
  assert.equal(p.start, "2026-12-01");
  assert.equal(p.end, "2026-12-25");
});

test("年をまたぐ期間", () => {
  const p = findPeriod("12/20〜1/10", today);
  assert.equal(p.start, "2026-12-20");
  assert.equal(p.end, "2027-01-10");
});

test("締切と発売日を読み取る", () => {
  const p = findPeriod("受注締切：12/5 23:59\n2027年1月20日 発売予定", today);
  assert.equal(p.deadline, "2026-12-05");
  assert.equal(p.release, "2027-01-20");
});

test("「〜まで」だけなら終わる日にする", () => {
  assert.equal(findPeriod("12/24まで限定販売", today).end, "2026-12-24");
});

test("過ぎた月日は来年とみなす", () => {
  assert.equal(findPeriod("2/14 発売", today).release, "2027-02-14");
});

test("日付がなければ何も入れない", () => {
  assert.deepEqual(findPeriod("今日は晴れ", today), { start: null, end: null, deadline: null, release: null });
});
