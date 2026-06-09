# PRD: Machi Koro — Online Multiplayer Platform

> **Status:** Draft v1.0 · **Owner:** Solo developer · **Last updated:** 2026-06-02
> **Strategy:** Hybrid — stabilize the live WordPress+WebSocket MVP, then migrate to a React + FastAPI + PostgreSQL commercial product.
> **Supersedes:** `MachiKoro WorkPlan.docx` (draft). Aligns with `MachiKoro_FullProductPlan.docx` as north star.

---

## Goal

Turn the existing playable Machi Koro MVP into a polished, cross-platform, **commercial freemium product** — a place where people play Machi Koro online with friends or AI, track their history, personalize their experience, and (optionally) pay for premium versions and cosmetics. Built solo, at a sustainable pace, correctness before speed.

## Target audience

- **Core:** Existing Machi Koro board-game fans who want to play online when they can't meet in person.
- **Social players:** Groups of 2–5 friends wanting a quick, low-friction online table (guest play, share a code).
- **Solo players:** People who want to play vs. AI or learn the game with a tactics advisor.
- **Region/launch:** English + Russian first (developer based in Almaty); Kazakh and others by demand.

## Problem

Machi Koro is a great in-person game, but playing remotely today means tabletop simulators (heavy, clunky) or nothing. There's no lightweight, polished, dedicated online Machi Koro that: works instantly in a browser, supports guest play, handles all three rule versions correctly, and remembers your games. The current MVP proves the concept but is **not safe for real players** (no per-action persistence, no socket auth, results not saved) and is **locked to a single version** with no path to versions/AI/mobile/monetization.

## Solution

A staged build on top of the validated MVP:

1. **Stabilize** the live MVP so real players can use it safely (persistence, auth, saved scores).
2. **Extract a clean, fully-tested game engine** (`machi_koro_engine/`) with per-version `GameConfig` (Basic / Harbour / Sharp).
3. **Migrate** the backbone to FastAPI + PostgreSQL and the UI to React + TypeScript (i18n from day one).
4. **Expand** into stats/history, AI opponent, mobile (React Native/Expo), cosmetics shop, and freemium monetization.

## Success Metrics

| Metric | Target (first commercial milestone) | Why |
|--------|-------------------------------------|-----|
| **Game completion rate** | ≥ 70% of started games reach a winner | Proxy for engine correctness + UX quality |
| **D7 retention (registered)** | ≥ 25% | Reason-to-return / "platform feel" working |
| **Avg. games per returning user / week** | ≥ 3 | Engagement loop health |
| **Crash-free / lost-game rate** | < 0.5% of games lost to errors/restarts | Stability bar for a live product |
| **Engine test coverage** | ≥ 80% lines, 100+ unit tests | Foundation correctness (FullProductPlan rule #1) |
| **Time-to-first-action** (table → first roll) | < 60s for a guest | Low-friction onboarding |
| **Free → paid conversion** | ≥ 3% of active users (post-monetization) | Freemium viability |
| **AI opponent adoption** | ≥ 30% of solo sessions use AI | Solo-play value |

## Scope (MoSCoW)

**Must Have**
- Stable live MVP: per-action state persistence, authenticated WebSocket, locked-down REST, persisted scores
- Clean extracted engine with `GameConfig` and ≥100 unit tests
- All three versions correct: **Basic**, **Harbour**, **Sharp**
- FastAPI + PostgreSQL backend; React + TS web frontend
- Lobby (create/join via code, optional password, waiting room), guest + registered auth (JWT)
- Real-time WebSocket sync, reconnection handling
- In-game history log + out-of-game stats dashboard
- Localization infrastructure (i18next) with English + Russian at launch

**Should Have**
- **Variable supply ("10-card market")** — only 10 establishment types are face-up at a time; when a type sells out, draw from a shuffled deck until 10 distinct types show again, so the market shifts each game (the expansions' recommended variant). A **free gameplay toggle** for the host (a mode, not paid content); most impactful with Harbour/Sharp, so it softly pulls toward the paid versions. Engine logic in Stage 1 (seedable RNG); market UI in Stage 3.
- AI opponent (Easy / Medium / Hard) + tactics advisor mode
- Mobile apps (iOS + Android) via React Native / Expo
- Cosmetics shop with earned currency (Koro Coins): avatars, backgrounds, card backs
- Leaderboards and head-to-head stats
- Public matchmaking / table browser improvements

**Could Have**
- Freemium monetization: Harbour Pass subscription, one-time version unlocks, coin bundles (RevenueCat + Stripe)
- Push notifications ("It's your turn"), haptics, sound effects
- Additional languages (Kazakh, etc.)
- Premium cosmetic packs, daily login bonuses, seasonal content

**Won't Have (this iteration)**
- Real-money trading or loot boxes
- Cross-game tournaments / ranked ladders
- User-generated content / custom card editors
- Voice/video chat
- Non-Machi-Koro game titles

## User Stories (epic-level)

> Detailed, sprint-ready stories live in the per-stage backlogs. These are the epics.

**Stage 0 — Stabilize (live MVP)**
- As a player, my game survives a server restart so a deploy doesn't erase our match.
- As a player, only the real seat occupant can act as my seat (no impersonation).
- As a registered player, my game results are saved so I have a record and a reason to return.

**Stage 1 — Engine**
- As the developer, I have a headless, tested engine module so every later stage just wires to it.
- As a host, I can choose Basic / Harbour / Sharp at table creation and the engine applies the right rules.
- As a host, I can enable a variable **"10-card" supply** so only 10 establishment types are available at once and the market shifts as types sell out (engine logic here in Stage 1; the stack-market UI in Stage 3).

**Stage 2/3 — Backend + Web**
- As a player, I can register, log in, or play as a guest.
- As a host, I can create a table (version, max players, optional password) and share a join code.
- As a player, I see a polished real-time board with dice animation, card activation highlights, and a turn indicator.
- As any player, I can read a scrollable, localized history log during the game.
- As a player, I can switch the interface language.

**Stage 4 — Stats**
- As a registered player, I can browse my past games and replay the round-by-round log.
- As a player, I can see my win rate and head-to-head record vs. a specific opponent.

**Stage 5 — AI**
- As a solo player, I can add an AI opponent at Easy/Medium/Hard to fill seats.
- As a learning player, I can enable a tactics advisor that recommends a buy and explains why.

**Stage 6 — Mobile**
- As a mobile player, I can install the app and play with the same account and games as web.

**Stage 7/8 — Shop + Monetize**
- As a player, I earn Koro Coins by playing and spend them on cosmetics.
- As a player, I can subscribe (Harbour Pass) or buy versions/coins to remove ads and unlock content.

## Technical requirements (non-functional)

- **Correctness:** Engine is the single source of truth for rules; ≥80% coverage, 100+ tests; deterministic (seedable RNG) for testing.
- **Architecture:** Headless engine (`machi_koro_engine/`) ← FastAPI backend (owns state) ← React / React Native clients. Versions = `GameConfig` objects; engine code is version-agnostic.
- **Persistence:** PostgreSQL; in-progress game state written after every action; per-round history retained permanently; migrations as code (Alembic).
- **Realtime:** WebSockets for game sync; graceful reconnect; turn-lock enforced server-side.
- **Security:** JWT auth; authenticated WebSocket (token per table/seat); no open REST endpoints; rate-limiting on table creation; hashed table passwords; server-authoritative actions (never trust client).
- **Performance:** Action → broadcast latency < 300ms p95; support 2–5 players/table; horizontally restart-safe (no game lost on deploy).
- **Localization:** i18next; all UI chrome, card names, effects, and event-log strings externalized to locale files. English + Russian at launch.
- **Observability:** Sentry error tracking (backend + frontend); structured logs.
- **CI/CD:** GitHub Actions runs tests on every push; auto-deploy on merge to main.
- **Platforms:** Modern browsers (desktop + mobile web); iOS + Android via Expo.
- **Compliance (monetization):** App Store / Play Store IAP via RevenueCat; Stripe for web; privacy policy, content rating.

## Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Live MVP loses in-progress games on restart (state in RAM only) | High | High | Stage 0 TASK-001: persist state per action; rehydrate on boot |
| Seat impersonation on unauthenticated WebSocket | High | High | Stage 0 TASK-002: signed per-seat token; server-authoritative actions |
| Refactoring the engine silently breaks card math (no tests today) | High | High | Stage 0 TASK-005 characterization tests; Stage 1 full suite before refactor |
| "Sharp" version underspecified (no confirmed card list) | Medium | Medium | Spike to confirm Sharp card list before Stage 1.2; treat as blocker, not assumption |
| Solo dev over-scopes; commercial vision stalls | High | High | Strict stage gating; ship Stage 3 (web) to real players before AI/mobile/monetize |
| Migration from WP/MySQL → React/FastAPI/Postgres drags on | Medium | High | Keep MVP live during migration; migrate behind the same engine; data migration plan in Stage 2 |
| i18n retrofitted late across many components | Medium | Medium | Wire i18next at the start of Stage 3, even if only EN/RU shipped |
| Mobile complexity (store review, native builds, IAP) underestimated | Medium | Medium | Mobile is Stage 6, not earlier; use Expo; prove web first |
| Monetization before product-market fit | Medium | High | Monetize only after retained players exist (Stage 8 last) |
| RNG/fairness disputes in multiplayer | Low | Medium | Server-side dice; logged, auditable events; seeded tests |

## Timeline

> Stages are **sequenced, not calendar-boxed** (solo dev, no fixed deadline). 2-week Scrum sprints; ~30 SP/sprint. Estimates are rough sprint counts, refined as each stage's backlog is built.

| Stage | Outcome | Est. sprints |
|-------|---------|--------------|
| **0 — Stabilize** | Safe, persistent, authenticated live MVP with saved scores | 1 |
| **1 — Engine** | Extracted, tested engine; Basic/Harbour/Sharp via GameConfig | 2–3 |
| **2 — Backend** | FastAPI + PostgreSQL, REST + WS, JWT, migrations | 2–3 |
| **3 — Web** | React + TS UI, lobby, history log, i18n (EN/RU) — **first real players** | 3–4 |
| **4 — Stats** | History storage + stats dashboard | 1–2 |
| **5 — AI** | AI opponent + tactics advisor | 2 |
| **6 — Mobile** | iOS + Android via Expo | 3–4 |

**⚠️ Team prerequisites (action required by owner):**
- **Create a `designer` agent BEFORE Stage 3.** No designer agent exists yet; Stage 3 (web UI), Stage 4 (dashboard), and Stage 7 (cosmetics) need wireframes/visual design/art. Blocking for Stage 3.
- **Create a `mobile-developer` agent BEFORE Stage 6.** Current web-developer covers React (web), not React Native/Expo, native builds, or store submission. Blocking for Stage 6.
| **7 — Shop** | Koro Coins + cosmetics | 2 |
| **8 — Monetize** | Subscription + IAP + Stripe | 2 |

**Critical sequencing rules:**
1. Stage 0 before any migration work — protect the live product first.
2. Stage 1 (tested engine) before Stages 2–8 — never skip it again.
3. **Create a `designer` agent before Stage 3** (web UI/art has no owner today).
4. Ship Stage 3 to real players before AI, mobile, shop, or monetization.
5. **Create a `mobile-developer` agent before Stage 6** (React Native/Expo not covered today).
6. Monetize last, only once retained players exist.
