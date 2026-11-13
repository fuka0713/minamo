import type { NextConfig } from "next";

// バックエンドの場所（compose の中では「backend」という名前で呼べる）
const BACKEND_URL = process.env.BACKEND_URL ?? "http://backend:4000";

const nextConfig: NextConfig = {
  // ブラウザからの /api/... を、そのままバックエンドに中継する
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*` }];
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
