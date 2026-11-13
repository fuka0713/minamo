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
