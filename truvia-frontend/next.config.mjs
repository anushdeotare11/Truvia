/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Do not redirect (and drop auth headers) when a path has a trailing slash.
  // The backend defines collection routes with a trailing slash (e.g. /cases/, /chat/),
  // so the proxy must forward those paths exactly as-is.
  skipTrailingSlashRedirect: true,
  eslint: { ignoreDuringBuilds: true },
  async rewrites() {
    const raw = (process.env.BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
    const backendUrl = raw.replace(/\/api(\/v1)?$/, "");
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "lh3.googleusercontent.com" },
    ],
  },
};

export default nextConfig;
