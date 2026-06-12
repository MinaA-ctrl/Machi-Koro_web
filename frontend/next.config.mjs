import createNextIntlPlugin from 'next-intl/plugin'

// Point the plugin at our request config so server components can read messages.
const withNextIntl = createNextIntlPlugin('./src/i18n/request.ts')

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // The backend (FastAPI) is reached via NEXT_PUBLIC_API_BASE; no rewrites needed
  // for REST. WebSocket connections go direct to NEXT_PUBLIC_WS_BASE.
  //
  // DEV ONLY: when running `next dev` standalone (no nginx in front), proxy /api
  // through the running nginx gateway on :8082 so REST is same-origin (the backend
  // has no CORS and its port isn't host-exposed). Inert in production.
  async rewrites() {
    if (process.env.NODE_ENV === 'production') return []
    return [
      { source: '/api/:path*', destination: 'http://localhost:8082/api/:path*' },
    ]
  },
}

export default withNextIntl(nextConfig)
