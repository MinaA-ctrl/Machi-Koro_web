# Machi Koro — Stage 3 frontend (Next.js 14, standalone output).
#
# Multi-stage: build with bun (the repo ships bun.lock), run on a slim node
# image using Next's standalone server bundle. The image is multi-arch and
# builds fine on the arm64 Hetzner CAX11 host.
#
# NOTE (deploy): the frontend is a BUILT image — `docker compose up` alone does
# NOT pick up source changes. After editing anything under frontend/, run
#   docker compose build frontend
# (same trap the backend has, see Stage 2 cutover-runbook QA-008.)

# ── deps ─────────────────────────────────────────────────────────────────────
FROM oven/bun:1-alpine AS deps
WORKDIR /app
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

# ── build ────────────────────────────────────────────────────────────────────
FROM oven/bun:1-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# NEXT_PUBLIC_* are inlined at build time. Prod default = same-origin via Caddy:
# REST under /api, WS derived from the page host (see frontend/.env.example).
ENV NEXT_PUBLIC_API_BASE=/api
ENV NEXT_PUBLIC_WS_BASE=/api
ENV NEXT_TELEMETRY_DISABLED=1
RUN bun run build

# ── runtime ──────────────────────────────────────────────────────────────────
FROM node:20-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

# Run as the unprivileged node user that ships with the image.
USER node

# Standalone bundle = server + the minimal node_modules it needs. Static assets
# (.next/static) are not included in the bundle and must be copied alongside.
COPY --chown=node:node --from=build /app/.next/standalone ./
COPY --chown=node:node --from=build /app/.next/static ./.next/static

EXPOSE 3000
CMD ["node", "server.js"]
