import type { NextConfig } from "next";

// バックエンドの場所（compose の中では「backend」「backend-py」という名前で呼べる）
const BACKEND_URL = process.env.BACKEND_URL ?? "http://backend:4000"; // Express
const BACKEND_PY_URL = process.env.BACKEND_PY_URL ?? "http://backend-py:8000"; // FastAPI

const nextConfig: NextConfig = {
  // ブラウザからの /api/... を、そのままバックエンドに中継する（上から順に当てはめる）
  async rewrites() {
    return [
      // FastAPI が担当するもの
      { source: "/api/screenshots", destination: `${BACKEND_PY_URL}/api/screenshots` },
      { source: "/api/screenshots/:path*", destination: `${BACKEND_PY_URL}/api/screenshots/:path*` },
      { source: "/api/docs", destination: `${BACKEND_PY_URL}/api/docs` },
      { source: "/api/openapi.json", destination: `${BACKEND_PY_URL}/api/openapi.json` },
      { source: "/api/py/:path*", destination: `${BACKEND_PY_URL}/api/py/:path*` },
      // それ以外は Express
      { source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*` },
    ];
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
