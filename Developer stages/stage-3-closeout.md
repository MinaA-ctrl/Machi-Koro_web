# Stage 3 Closeout — Frontend: React + TypeScript rebuild with i18n (EN/RU)

> **Status (2026-06-19): COMPLETE & LIVE.** The final tier of the PRD migration is
> done. The React + TypeScript frontend is the production frontend at
> **https://machi-koro.pima.kz** (React → FastAPI + Postgres via Caddy). WordPress is
> out of the serving path. Stages 0–3 of the PRD migration are complete.

## Goal (recap)
Replace the WordPress-hosted vanilla-JS UI with a React + TS app built from the
"Cozy Tabletop" design tokens, on the Stage-2 FastAPI backend, localized EN/RU,
accessible, responsive — playing Basic/Harbour/Sharp/Variable-Supply at parity.

## Phase status (S3.0–S3.8)
| Phase | State |
|---|---|
| S3.0 Design handoff & tokens | ✅ done |
| S3.1 Scaffold + design system + i18n wiring | ✅ done |
| S3.2 Auth + lobby flow | ✅ done (guest + registered, create/browse/join, waiting room, lobby WS) |
| S3.3 Game board core | ✅ done (top bar, opponents, dice + animation, market, Your City, prompts) |
| S3.4 Market + Sharp prompts + 10-card VS + WS contracts | ✅ done (WS event/animation contract implemented; buy-flow bug fixed) |
| S3.5 i18n EN/RU complete + keyed events | ✅ done — **card-effect translations were the last gap, now closed** (`cardEffects` catalog + `useCardEffect`) |
| S3.6 Responsive / mobile | ✅ done for scope — desktop + responsive; **phone pass added** (login visible on phone, reaction bar reflow, market carousel, trimmed top bar). Full native-style phone redesign remains intentionally deferred (product decision). |
| S3.7 QA, accessibility & hardening | ✅ functionally complete — extensive manual multi-client testing + many fixes; build/typecheck/lint green. **Residual (optional):** a formal Lighthouse + screen-reader sweep was not run as a separate audit. |
| S3.8 Cutover & retire WordPress | ✅ done — production serves React; WP out of the serving path |

## Shipped in the Stage-3 finishing run (2026-06-17 → 06-19)
All deployed to production unless noted.
- **Gameplay/UX:** buy-flow fix (`type:'card'`), buy confirmation dialog, foldable
  turn-grouped game history, emoji **reaction thought-bubbles**, **coin gain (green)
  / loss (red) toasts**, tap-a-player to view their cards/landmarks, coin balance
  moved next to "Your City", removed "Play Again", **📋 landmark-descriptions modal**.
- **Stats seam (Stage-4 head start):** per-game **points** + game history + account
  total (`scores.points` column, migration `0007_add_score_points`, `/me/stats`).
- **Lifecycle:** finished tables retire to `finished` when emptied → active-games /
  players-online counts drop (scores preserved for history).
- **Accounts:** unique registered display names (case-insensitive); exact-match email
  (one account per exact email) with an "account exists — go to log in" flow.
- **Polish:** market sorted by family + ascending dice; long card names fit one row;
  hover-to-enlarge cards; rename UX (guest placeholder, registered prefilled,
  select-all on open); **synthesized sound effects** (dice/coins/build/turn/win) with
  a persisted mute toggle; **landing page** at `/landing` (wordmark entry), bilingual,
  describing only currently-real features.

## Production state
- Frontend: `machi-koro_web-frontend` (Next.js standalone). Backend:
  `machi-koro_web-backend` (FastAPI, applies Alembic on boot). DB: Postgres 16.
  Edge: Caddy (auto-TLS).
- Migrations through `0007_add_score_points` applied in prod.
- Deploys are surgical file-sync + container rebuild; pre-deploy source backups kept
  on the host (`~/mk-backup-*.tgz`).

## Definition-of-done check
- ✅ React is the live frontend; WordPress removed from serving path.
- ✅ Basic/Harbour/Sharp/Variable-Supply play at parity; server-authoritative.
- ✅ Localized EN/RU including the game log and card names **and effects**.
- ✅ Engine emits keyed (translatable) events.
- ✅ Responsive desktop + phone-usable.
- 🟡 Formal WCAG/Lighthouse audit not separately run (functionally a11y-conscious;
  flagged for a later hardening pass if desired).

## Handoff → Stage 4 (Stats) and beyond (PRD)
- **Stage 4 — Stats:** partially started (points, history, account totals shipped).
  Remaining: richer stats surfaces / leaderboards, profile page.
- **Stage 5 — AI** opponent.
- **Stage 6 — Mobile** (React Native / Expo native app).
- **Stage 7/8 — Shop + Monetize:** Koro Coins currency, cosmetics shop, freemium
  (Harbour Pass, version unlocks). Backend already carries the entitlements/wallet
  seam; the "Market" page is a live "coming soon" placeholder.

**Stage 3 = DONE. The PRD web migration (Stages 0–3) is complete and in production.**
