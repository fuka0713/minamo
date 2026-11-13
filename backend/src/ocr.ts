// 文字認識（OCR）：コンテナに入れた Tesseract で、画像から日本語と英語の文字を読み取る
import { spawn } from "node:child_process";

export function readText(image: Buffer): Promise<string> {
  return new Promise((resolve) => {
    // 「tesseract stdin stdout -l jpn+eng」= 画像を渡して、読み取った文字を受け取る
    const tesseract = spawn("tesseract", ["stdin", "stdout", "-l", "jpn+eng"]);
    let text = "";
    tesseract.stdout.on("data", (chunk) => (text += chunk));
    tesseract.on("close", () => resolve(text.trim()));
    tesseract.on("error", () => resolve("")); // Tesseract がない環境では空にする（登録は続ける）
    tesseract.stdin.on("error", () => {});
    tesseract.stdin.end(image);
  });
}
