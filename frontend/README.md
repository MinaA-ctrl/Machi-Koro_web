# Machi Koro — Frontend (Stage 3)

React + TypeScript rebuild of the Machi Koro UI from the **"Cozy Tabletop"
(Tabletop Hearth)** design system, talking to the Stage-2 FastAPI backend.
Parallel build (strangler-fig) — it replaces the WordPress page-host at parity.

## Stack
- **Next.js 14 (App Router)** + React 18 + **TypeScript strict**
- **Tailwind** — theme = the committed `DESIGN.md` tokens (`tailwind.config.ts`)
- **Zustand** (game/UI state) + **TanStack Query** (REST)
- raw **WebSocket** client for the live lobby/game channels
- **next-intl** (EN + RU), locale prefix routing (`/en`, `/ru`)

## Run
```bash
bun install
cp .env.example .env.local      # point at the FastAPI backend
bun run dev                     # http://localhost:3000  → /en
```
Other scripts: `bun run build`, `bun run start`, `bun run typecheck`,
`bun run lint`, `bun run test` (vitest), `bun run test:e2e` (playwright).

`.env.local`:
- `NEXT_PUBLIC_API_BASE` — FastAPI REST base (e.g. `http://localhost:8000`)
- `NEXT_PUBLIC_WS_BASE` — WS base (e.g. `ws://localhost:8000`)

## Status by phase
| Phase | State |
|-------|-------|
| **S3.1** scaffold + design system + i18n | ✅ **done** — typecheck/lint/build green; `/en` + `/ru` render; styleguide at `/en/styleguide` |
| **S3.2** auth + lobby flow | ✅ **implemented** — guest bootstrap, create/browse/join-by-code, waiting room, password modal, **lobby WebSocket** live presence + kicked/table-closed overlays, toasts. *Remaining:* live two-client smoke + Playwright e2e. |
| **S3.3** board core | 🟢 **implemented + contract-verified + browser-verified** — top bar + phase pill, opponents strip, animated dice (reduced-motion snap), market buy, Your City + Milestones, Harbour prompts (harbor/reroll/tuna), winner + rematch. Builds green; REST+WS contract driven end-to-end against the live backend (two clients, all assertions passed); the board layout rendered + screenshotted in a real browser (EN + RU) via the fixture route. **Remaining:** a full game *to a win* incl. live Harbour prompts (QA / S3.7). |

### Visual verification
- `/[locale]/styleguide` — the design atoms (browser-verified: pinned family colors, token-press buttons, embossed coins, paper elevations).
- `/[locale]/board-preview` — **dev-only** fixture render of the board (`lib/board-fixture.ts` + `components/board/BoardView`), used for design review/screenshots without a backend. The live board is `/game/[code]`.
- Lobby (EN/RU), styleguide, and the board (EN/RU) were rendered in headless Chromium and matched the Stitch references. Card names + game-log text still render English in RU — that's the **engine keyed-events** dependency (S3.5), not a frontend miss.
| **S3.4** market + Sharp prompts + 10-card VS | 🟢 **implemented + browser-verified** — consumes the engine's `game_prompt` payload; overlays for TV Station, Cleaning Company (type-pick), Demolition (landmark-pick), Moving Company (give: card→recipient), Business Center (trade), plus harbor/reroll/tuna; Tech Startup invest button; 10-card Variable-Supply remaining-count chips + flip-reveal (diffs `state.market`; reduced-motion → fade). All overlays + VS market screenshotted in-browser (EN/RU). **Backend already ships the contract** (`game_prompt` + timeout auto-resolve in `app/ws.py`). **Remaining:** exercise a live Sharp/VS game to a win (QA). |
| **S3.5** RU i18n + keyed log + expansion-safe | 🟢 **largely done + browser-verified** — UI chrome, card/landmark **names**, all interactive prompts, and the **game log localized from the engine's keyed `state.events`** (`use-event-text` over the `log` catalog; `cards` catalog for names). RU board/prompts screenshotted; text wraps/truncates with no overflow. **Remaining:** card *effect* descriptions (rules text) — engine free-text, needs a `cardEffects` catalog (44 entries) routed through `EstablishmentCard`; the name/log mechanism is already in place. |
| **S3.6** responsive (mobile deferred) | 🟢 **responsive done** — layout adapts across desktop/tablet/narrow widths: board two-col ≥1024 / stacked below; lobby two-col ≥1024 / stacked below (was `md`, raised to `lg` to fix a cramped 768–1023 zone); market scrolls, top bar + opponents wrap. Verified in-browser 720–1100px, no horizontal overflow. **Phone-specific patterns (carousel, bottom-nav, 44px thumb targets) intentionally deferred** per product decision. |

### i18n architecture (S3.5)
- **UI strings** → `messages/{en,ru}.json` via `next-intl` (`useTranslations`). No hardcoded UI strings (only the dev Styleguide has literal atom labels).
- **Card/landmark names** → `cards` catalog, resolved by `useCardName(id, fallback)` (`lib/i18n-names.ts`). Routed through every surface: market, Your City, Milestones, prompts.
- **Game log** → localized from the engine's keyed `state.events` (`{t, seq, ...params}`) by `useEventText()` (`lib/use-event-text.ts`) over the `log` catalog — one template per event type; ids resolved to names. Falls back to English `state.log` for pre-keyed snapshots. The `GameLog` component renders it.
- **Expansion-safe:** no fixed-width buttons; long RU strings truncate (`truncate`) or wrap (`line-clamp`); verified in-browser (e.g. "Достопримечательности", "Парк развлечений", "Клининговая компания").

### Game board architecture (S3.3)
- `src/store/game-store.ts` — zustand mirror of the server's `state_update` snapshot. The UI never mutates game fields; every action round-trips.
- `src/lib/use-game-socket.ts` — game channel (`/ws/{code}/game/{seat}?token=…`), 4401-aware (no reconnect on bad token).
- `src/lib/game-actions.ts` — exact `handle_action` message shapes (roll / build / skip_build / prompt_response / tuna_roll / new_game).
- `src/components/board/*` — `GameBoard` (orchestrator) → `BoardTopBar`, `OpponentsStrip`, `FeltTable` + `Dice`, `Market` + `EstablishmentCard`, `YourCity`, `PromptOverlay`, `WinnerOverlay`.
- The structured Sharp prompt (type/options) already arrives inside `state.pending_prompt` — S3.4 renders choice UIs from it.

## Design tokens — the one source of truth
Everything visual references a token in **`tailwind.config.ts`** (mirrored as CSS
vars in `src/styles/globals.css` for non-utility contexts). **No stray hex values
in components** — verify with:
```bash
grep -rnE '#[0-9a-fA-F]{3,8}' src --include='*.tsx' --include='*.ts' | grep -v globals.css
```
The four establishment-family colors are pinned exactly:
`blue #5DADE2 · green #7ABF7E · red #E08470 · purple #A98BC4` (`colors.family.*`).

## Backend contract consumed
REST (`src/lib/api.ts`, types in `src/types/api.ts`) — mirrors
`websocket-server/app/schemas.py`:
`/auth/{guest,login,register,refresh,me}`, `/tables` (create/list),
`/tables/{code}/{join,start,kick,rename}`, `/tables/{code}`.
WS event types modeled in `src/types/game.ts` from `app/ws.py`
(`state_update`, `game_toast`, `coin_event`, `prompt`, lobby join/left/kicked/closed).

## Accessibility built in (S3.1)
- `prefers-reduced-motion` neutralized globally + a reactive hook for structural cases.
- Gold focus ring on `:focus-visible`; Modal traps focus + restores it + Escape.
- Family-band ink chosen for ≥ AA contrast (dark ink on every band).
- Toasts are an `aria-live` region; coin/dice atoms carry `aria-label`s.

## Open gaps to raise (PM / backend)
1. **Lobby WS contract** — `app/ws.py` relays arbitrary lobby messages and emits
   `player_joined/left/kicked` + `table_closed`. We need the agreed message shape
   for **kick** (does the kicked seat get a dedicated event, or infer from the
   relayed `player_kicked`?) to drive the kicked overlay instantly. Until then the
   waiting room polls.
2. ~~**Sharp prompt payloads (S3.4)**~~ — RESOLVED. The backend now emits a
   structured `game_prompt` (engine `build_prompt_payload`: type/params/options/
   default/timeout) + auto-resolve on timeout, and re-emits on reconnect. The
   frontend consumes it (`use-game-socket` → store `currentPrompt` → `PromptOverlay`).
3. ~~**Keyed/translatable log (S3.5)**~~ — RESOLVED. The engine emits keyed
   `state.events`; the log is localized from them (`use-event-text`). REMAINING:
   `game_toast` text is still an English string from the engine (the granular
   `game_events` keyed stream could replace toasts for full localization), and card
   *effect* descriptions need a `cardEffects` catalog.
4. **Fredoka has no Cyrillic subset** — RU headings fall back through the font
   stack. Consider a Cyrillic-capable rounded display face before RU sign-off.
5. **10-card mobile market reveal** — the Stitch mobile variant was weak; desktop
   reveal (`10_card_market_reveal_desktop`) is the reference for S3.4.
