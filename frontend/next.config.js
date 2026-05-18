/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // In dev, proxy /api/* to the FastAPI server on :8000 so the frontend
  // can call /api/analyze without CORS issues. In production, point this
  // at your deployed FastAPI URL via NEXT_PUBLIC_API_BASE_URL.
  async rewrites() {
    const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
    return [
      { source: "/api/:path*", destination: `${apiBase}/api/:path*` },
    ];
  },
};

module.exports = nextConfig;
