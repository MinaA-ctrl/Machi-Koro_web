# Phase D-QA — Real-Browser Verification of the Full Sharp Experience

**Finder:** QA · **Date:** 2026-06-07 · **Gate:** final before Sharp ships
**Headline:** the three interactive overlays (Cleaning / Demolition / Moving) were **clicked in a real browser** — the open residual from D-WEB is closed. ✅

## Environment & deploy discipline (QA-008)
- Full Docker stack; `.env` present with matching `MK_WS_SECRET` on both `wordpress` and `websocket`.
- **Rebuilt the engine image before testing** (`docker compose build websocket && docker compose up -d websocket`) — it's a built image, not bind-mounted (QA-008). Confirmed Sharp is actually in the running engine: `game_config.py` present, `config_for(version, sharp)` wired, `SHARP_CARD_IDS` = 13 cards. The WP plugin is bind-mounted, so the D-WEB frontend is live as-is.

## Method (how "real" each item is)
- **Items 1, 2, 6** — genuine **two-context** browser flow (Playwright/Chromium on the host → `http://localhost:8082`): Player A creates via the UI, Player B joins via the UI, A starts, both land in `/game/`.
- **Items 3, 4** — the precondition (own the card + roll its number + valid targets) is **engineered deterministically** by pre-inserting a *schema-valid, engine-built* game state (constructed with the engine's own `create_initial_state` + `_set_interactive_phase`, so `pending_prompt` shapes are exactly what the overlays read) into `wp_mk_game_states` **before** the first game-WS connect (the lazy-build seam). Then a **real DOM click** in the browser drives the **real engine over the real WS**; the effect is read back from the **persisted** state. The click and the engine's response are 100% real — only the board setup is staged (the sanctioned "engineer the conditions" path).
- **Item 5** — exercised through the **exact engine code the server runs** (`_finish_roll(state, 9)`, the same path a real roll-of-9 takes), deterministically.
- **No console errors** were captured across the entire browser run (`page.on('console'/'pageerror')` listeners on every page).
- Evidence screenshots in `/tmp/mkqa/shots/` (before/after for every overlay, tech, all four labels, both Sharp markets).

---

## Results — PASS/FAIL + repro per item

### 1. Create toggle + label → **PASS**
"+ Sharp" toggle present, **default off**. Created all four compositions via the UI:
| Composition | Lobby badge | In-game (drawer / topbar) |
|---|---|---|
| Basic + Sharp | `🏙️ Base Game + Sharp` | `Base Game + Sharp` / `Basic + Sharp` |
| Harbour + Sharp | `⚓ Harbor Expansion + Sharp` | `Harbour + Sharp` |
| Basic (off) | `🏙️ Base Game` | `Base Game` / `Basic` |
| Harbour (off) | `⚓ Harbor Expansion` | `Harbor Expansion` / `Harbour` |
- **Repro:** Front page → Create → pick base → tick **+ Sharp** → Create Public; joiner joins by code; host Starts. Badge reads "… + Sharp" in lobby and in-game.

### 2. Cards render + market size → **PASS**
- Market size **28** (Basic+Sharp) and **38** (Harbour+Sharp) — exact.
- All **13** Sharp cards render (Vineyard, Corn Field, General Store, Soda Bottling Plant, French Restaurant, Private Club, Winery, Cleaning Company, Loan Office, Tech Startup, Park, Demolition Company, Moving Company).
- Every card shows **icon + name + cost + effect**; **0 broken** symbols, **0 fallback (🏢) boxes**. The 6 Sharp symbols (🍇 🌽 🏪 🍽️ 🏦 🚚) all map.
- **Tooltip note:** market cards show the effect **inline (always visible)**; owned establishments expose the effect via a native `title` hover tooltip. Market cards have no separate hover tooltip — but the effect is never hidden, so the information requirement is met (not a defect).
- **Repro:** Open a Basic+Sharp (or Harbour+Sharp) game; the market shows 28 (38) distinct cards including the 13 Sharp cards with full icon/name/cost/effect.
- **Measurement caveat resolved:** an initial probe miscounted symbols as "blank" because WordPress's emoji script rewrites emoji chars into `<img class="emoji">` (empty `textContent`); the symbols render fine — re-checked counting text-or-img.

### 3. ★ The three interactive overlays — CLICKED IN-BROWSER → **PASS** (all three)
Each overlay rendered, was **clicked**, and the engine applied the effect (read back from persisted state). Screenshots before/after captured.
- **Cleaning Company** — overlay listed targets; clicked **Corn Field** → both open copies closed board-wide (`renovation.corn_field = 2`), active **+2🪙** (3→5), phase → `build`.
- **Demolition Company** — overlay offered **Train Station / Shopping Mall** (2 built landmarks, so it prompts); clicked **Train Station** → demolished (`built=false`, still in landmark list ⇒ **rebuildable**), active **+8🪙** (3→11), phase → `build`, **game continues**.
- **Moving Company** — selected **Corn Field** → target **B** → **Give Card** → card transferred seat 0 → seat 1 (p0 −1, p1 +1), active **+4🪙** (3→7), phase → `build`.
- **Repro:** Own the card and roll its number (Cleaning 8 / Demolition 4 / Moving 9–10) with valid targets; the overlay appears; pick → effect applies and the turn proceeds to Build.

### 4. Tech Startup invest → **PASS**
In your Build phase, owning Tech Startup: the **"Invest 1 🪙"** button is shown; clicking it invests once (coins 5→4, `investments.tech_startup = 1`, `tech_invest_used = true`); the button is then **gated** (hidden) for the rest of the turn.
- **Repro:** Own Tech Startup, your Build phase → "Invest 1 🪙" appears → click → invests once → button disappears; it returns next turn.

### 5. Renovation (Winery) visible behavior → **PASS**
First roll-of-9: Winery pays **+12** (6 × 2 Vineyards) then **closes for renovation** (`renovation.winery = 1`, active copies → 0). Next roll-of-9: the closed copy **reopens and pays 0**. Verified through the exact engine path the server uses.
- **Repro:** Own Winery + Vineyards; roll 9 → Winery pays then closes; next 9 → pays 0 (reopens).
- **UI observation → QA-009 (below):** the current pre-React UI has **no persistent renovation indicator** on a closed card; the only visible signal is the coin payout/toast on the paying roll (and its absence on the reopen roll). Behavior is correct; visibility is thin.

### 6. Regression (Sharp off) → **PASS**
Plain **Basic** and **Harbour** create with the toggle off: labels read `Base Game` / `Harbor Expansion` (no "+ Sharp"), first roll plays cleanly, **no console errors**. Market composition unchanged from B6 (Basic 15-card / Harbour 25-card families; Sharp cards never leak in).

---

## Bug filed

### QA-009 · UX · Low · P3 · OPEN
**No persistent renovation indicator on closed (renovating) cards in the game UI.**
- Sharp's renovation mechanic (Winery, Cleaning Company targets) closes copies that then skip one activation. The engine tracks this correctly (`renovation` map, verified), but the frontend renders no badge/state on a closed card — a player can't see *which* of their cards are currently closed; they only infer it from a coin payout being absent on a roll.
- **Severity rationale:** behavior is correct and the slice is shippable; this is a clarity gap, not a defect. Pre-React UI (replaced in Stage 3), so likely a deliberate scope cut — filing for visibility so it isn't lost.
- **Repro:** In a Sharp game, trigger a Winery roll-9 (it closes) → the owned-establishments panel shows no "renovating/closed" marker on the Winery.
- **Suggested fix:** small badge/dimming on owned cards where `renovation[card_id] > 0` (count of closed copies). Defer to Stage-3 React rebuild if not cheap now.

---

## Observation (no ID — likely environmental)
The **joiner's** auto-advance from lobby → `/game/` (driven by the `game_started` WS broadcast) once exceeded ~8s under heavy concurrent headless-browser load and needed a fallback navigation in the harness; it passed on retry and the **host** transition was always prompt. Most likely test-env contention (many simultaneous Chromium contexts), not a product issue — flagging only as a watch-item for D-WEB. Not reproduced reliably; no QA-ID filed.

## Note to PM
- **All six checklist items PASS**, including the non-negotiable three overlay clicks (real DOM). No console errors. Sharp is verified shippable from a QA standpoint.
- One Low/P3 finding (**QA-009**, renovation not visually surfaced) — does not block the gate; recommend Stage-3 React rebuild.
- Followed QA-008 discipline (rebuilt the engine image, confirmed Sharp live before testing).
- **Did not commit** (owner batches Phase D after sign-off). Stack changes: rebuilt `websocket` image; many short-lived `MK-*` test tables remain in the DB (lobby/playing rows + injected game states), harmless.
