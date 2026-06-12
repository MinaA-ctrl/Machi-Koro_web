# Stage 3 Plan — Frontend: React + TypeScript rebuild with i18n (EN/RU)

> **Status (2026-06-11): PLANNED.** The final tier of the PRD migration. Replace the
> WordPress-hosted vanilla-JS UI with a **React + TypeScript** app, built from the
> new **"Cozy Tabletop" design system**, talking to the Stage-2 FastAPI backend, and
> shipping in **English and Russian**. The live game plays identically throughout.
> **Builds on:** Stage 2 complete — single FastAPI + Postgres backend, JWT auth
> (guest + registered), `machi_koro_engine` as a package, the free entitlements seam,
> Alembic migrations, WordPress demoted to page-host.
> **Prereq met:** the `designer` agent exists; a Stitch design set + `DESIGN.md`
> token system has been produced and reviewed.

## Goal
A **React + TS** frontend that owns all game UI — lobby, board, market, dice,
interactive prompts, modals — implemented from committed design tokens, wired to the
existing FastAPI REST + WebSocket backend, localized **EN/RU**, accessible (WCAG AA),
and responsive (desktop + mobile). At parity it **replaces the WordPress page-host**,
which is then retired.

## Strategy
- **Strangler-fig, parallel build.** Stand up the React app alongside the live WP-JS
  UI; cut over only at proven parity. The shared `machi_koro_engine` means rules never
  fork — the frontend is a view over the same server-authoritative state.
- **System first, screens second.** Port `DESIGN.md` into committed Tailwind tokens
  and a base component library *before* building screens, so nothing is restyled twice.
- **Backend is mostly done.** Stage 2 delivered auth, persistence, REST + WS, engine.
  Stage 3 is a frontend job on top of it — backend touches are limited to a few WS
  message contracts and the engine's i18n-ready event refactor (below).

## Design inputs (already produced)
- `DESIGN.md` ("Tabletop Hearth") — color/type/spacing/radius/elevation tokens + component specs. **Token source of truth.**
- Stitch screen set: lobby, browse, waiting room, game board (desktop + mobile),
  card interaction, **10-card market reveal (desktop)**, dice-roll 3-frame animation,
  interactive prompts (4 Sharp types), password modal, kicked/closed overlays, toasts,
  victory.
- **Cleanup owed before handoff:** delete the stale `market_dynamics/` diagram; the
  `10_card_market_reveal/` *mobile* variant is weak (empty slots) — redo or drop it.

## Key decisions (recommended defaults — confirm or override)
| # | Decision | Recommended default |
|---|----------|---------------------|
| 1 | Framework | **Next.js (App Router) + React + TypeScript strict** (per `web-developer` settings) |
| 2 | Styling | **Tailwind**, theme = `DESIGN.md` tokens ported into `tailwind.config.ts` |
| 3 | State / data | **Zustand** (game/UI state) + **TanStack Query** (REST); raw WS client for live game |
| 4 | i18n | **`next-intl`**, EN + RU message catalogs; locale switch in UI; default from account `language` |
| 5 | Build alongside | **Parallel**; cut over at parity, then retire the WP page-host + plugin JS |
| 6 | Engine log strings | **Refactor to structured/keyed events** in this stage (the D1-deferred i18n follow-on) so the game log + prompts are translatable |
| 7 | Mobile | **Responsive in-scope** (desktop-first board, mobile carousels), no native app |

## Phases

### S3.0 — Design handoff & token source of truth  · Designer / PM  *(keystone)*
- [ ] Consolidate the Stitch set; delete the stale market diagram; finalize the mobile market.
- [ ] Convert `DESIGN.md` into a committed token spec (CSS vars + Tailwind keys), pin the **exact** family hexes (`#5DADE2/#7ABF7E/#E08470/#A98BC4`), and write component specs with full state matrices + the **motion specs** (Stitch gave only static frames).
- **AC:** one handoff doc per surface; tokens unambiguous; a11y notes (contrast, focus, reduced-motion) attached.
- **DoD:** handoff lives in *Developer stages*; `web-developer` can build with no guesswork.

### S3.1 — Frontend scaffold + design system  · Web
- [ ] Next.js App Router + TS strict + Tailwind; port tokens into `tailwind.config.ts`; load Fredoka/Nunito.
- [ ] Base UI atoms: Button (token "token-press" style), PaperCard, CoinChip, Modal, Toast, FamilyBand, DiceNumberBadge.
- [ ] Wire `next-intl`; scaffold EN/RU catalogs (keys, not yet fully translated).
- **AC:** Storybook (or a styleguide route) renders the atoms matching `DESIGN.md`; locale toggle flips a sample string EN↔RU.
- **DoD:** CI lints/builds; tokens are the only styling source (no stray hexes).

### S3.2 — Auth + lobby flow  · Web
- [ ] JWT guest + registered against FastAPI; token refresh; account `language`.
- [ ] Screens: home (create/browse/join + game-setup: Basic/Harbour, +Sharp, 10-card), waiting room, password modal, kicked/closed overlays, toasts. WS **lobby** channel.
- **AC:** create → join (public + by-code + password) → start works against the real backend with no regressions vs. WP-JS.
- **DoD:** auth + lobby e2e (Playwright); real-browser smoke from a second client.

### S3.3 — Game board core  · Web
- [ ] Board layout per spec: top bar (name · turn banner · **phase pill** · coin balance), opponents strip (avatar · coins · mini owned-cards · turn highlight), action area (dice + Roll), card market, **Your City** owned-cards drawer.
- [ ] Dice roll + **animation** (idle → tumble → result), coin transactions, turn/phase via WS **game** channel.
- **AC:** a full **Basic** and **Harbour** game plays to a win against the live backend, server-authoritative, no rules fork.
- **DoD:** real-browser multi-client play-through; `prefers-reduced-motion` honored.

### S3.4 — Market, Sharp prompts & Variable Supply  · Web + Backend
- [ ] Card buy from market; **Sharp interactive prompts** (Cleaning Company type-pick, Demolition landmark-pick, Tech Startup invest, Moving Company give).
- [ ] **10-card Variable-Supply** market UI with the buy→empty→reveal animation; remaining-count chips.
- [ ] **Backend:** confirm/add WS message types for interactive prompts + market-reveal events (engine already exposes the 10 stacks via `state.market`; small, not a rebuild).
- **AC:** Sharp + 10-card games play end-to-end; prompts resolve server-side; reveal animates on stack sell-out.
- **DoD:** WS contract documented; QA parity on all four mode combos (Basic/Harbour × ±Sharp × ±VS).

### S3.5 — i18n EN/RU complete + engine keyed events  · Web + Backend
- [ ] Full RU translation; locale switch UI; **expansion-safe** layout pass (~30% RU growth — no fixed-width button overflow).
- [ ] **Backend/engine:** refactor English log strings → structured/keyed events (the D1-deferred follow-on) so the game log + prompt text are translatable.
- **AC:** the entire UI + game log renders correctly in RU with no truncation/overflow; switching locale needs no reload.
- **DoD:** i18n lint (no hardcoded strings); RU screenshot review; keyed-event tests green.

### S3.6 — Responsive / mobile  · Web
- [ ] Mobile board (vertical stack, horizontal opponent chips, market carousel, bottom nav, thumb targets); mobile lobby/waiting/modals.
- **AC:** a full game is playable on a phone viewport; no horizontal scroll; tap targets ≥ 44px.
- **DoD:** mobile real-browser play-through (iOS Safari + Android Chrome).

### S3.7 — QA, accessibility & hardening  · QA
- [ ] Contrast audit of ink-on-family-band (AA), keyboard nav + focus order, reduced-motion, screen-reader labels on dice/coins/cards.
- [ ] Full regression vs. WP-JS across all modes; Lighthouse (perf + a11y).
- **AC:** WCAG AA met; no P0/P1 regressions; Lighthouse a11y ≥ 90.
- **DoD:** QA report in *Developer stages*; sign-off to cut over.

### S3.8 — Cutover & retire WordPress  · Web / PM / owner
- [ ] Point nginx `/` at the React app; retire the WP page-host + plugin JS/CSS; delete legacy UI.
- [ ] Update the cutover runbook; confirm rollback path.
- **DoD:** React is the live frontend; WordPress fully removed from the serving path. **PRD migration (Stages 0–3) complete.**

## Sequencing
S3.0 (handoff) → S3.1 (scaffold + system) → S3.2 (auth + lobby) → S3.3 (board core)
→ S3.4 (market + Sharp + VS) ∥ backend WS contracts → S3.5 (i18n + keyed events)
→ S3.6 (mobile) → S3.7 (QA/a11y) → S3.8 (cutover). Real-browser checks throughout;
parity sign-off before cutover.

## Risks
| Risk | P | Impact | Mitigation |
|------|---|--------|------------|
| Scope creep — "rebuild + redesign + i18n at once" (solo dev) | High | High | System-first; ship lobby+board parity before Sharp/VS polish; mobile after desktop |
| Token drift from `DESIGN.md` (stray hexes, off-brand) | Med | Med | One token source in `tailwind.config.ts`; lint for raw hex; styleguide route |
| Engine log refactor reintroduces rules bugs | Med | High | Behavior-identical keyed-event swap; 182 engine tests guard it; do it isolated (S3.5) |
| RU text overflow breaks layouts | Med | Med | Expansion-safe pass; no fixed-width buttons; RU screenshot review |
| WS contract gaps for prompts / reveal | Med | Med | Define message types in S3.4 with backend; document; parity tests per mode combo |
| Two UIs live during cutover | Med | Med | Parallel build; cut over only at proven parity; rollback = redeploy prior commit |
| a11y fails on colored family bands | Med | Med | Contrast audit in S3.0 spec + S3.7 verify; adjust band/ink tokens early |

## "Stage 3 done" =
A **React + TS** frontend, built from the committed **Cozy Tabletop** tokens, playing
Basic/Harbour/Sharp/Variable-Supply at parity against the Stage-2 FastAPI + Postgres
backend, **localized EN/RU**, **WCAG AA**, responsive on desktop + mobile, with the
**engine emitting keyed (translatable) events**. WordPress is removed from the serving
path. **The PRD migration (Stages 0–3) is complete.** Next: feature stages (7/8
monetization, etc.).

**Estimate:** 3–4 sprints (frontend-heavy; backend touches are small).
