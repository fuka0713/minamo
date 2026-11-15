"use client";

// ログイン・アカウント登録の画面
import { useRouter } from "next/navigation";
import { useState } from "react";
import { login, signup } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [isSignup, setIsSignup] = useState(false); // true = アカウント登録 / false = ログイン
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault(); // ページの再読み込みを止める
    try {
      if (isSignup) await signup(email, password);
      else await login(email, password);
      router.push("/"); // うまくいったらトップへ
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "うまくいきませんでした");
    }
  }

  return (
    <form onSubmit={handleSubmit} className="mx-auto max-w-sm space-y-4">
      <h1 className="text-xl font-bold">{isSignup ? "アカウント登録" : "ログイン"}</h1>

      <p className="text-sm text-gray-500">メールアドレス</p>
      <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required className="input" />

      <p className="text-sm text-gray-500">パスワード{isSignup && "（8文字以上）"}</p>
      <input
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        type="password"
        required
        minLength={isSignup ? 8 : undefined}
        className="input"
      />

      <button type="submit" className="chip chip-on w-full">
        {isSignup ? "登録する" : "ログインする"}
      </button>
      {message && <p className="text-sm text-red-600">{message}</p>}

      <button type="button" onClick={() => setIsSignup(!isSignup)} className="text-sm text-gray-500 underline">
        {isSignup ? "アカウントをお持ちの方はログイン" : "はじめての方はアカウント登録"}
      </button>
    </form>
  );
}
