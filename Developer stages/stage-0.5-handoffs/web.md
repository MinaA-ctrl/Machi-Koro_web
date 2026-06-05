# Handoff → Web Developer · Stage 0.5 (Frontend Polish)

> Paste into a `web-developer` session. Code: `~/Programming projects/Vibe_coding/Claude_Antropic/Machi Koro project`.
> ⚠️ Stack: **WordPress plugin, vanilla JS / CSS** — `wp-plugin/machi-koro/assets/style.css`, `assets/app.js`, `includes/shortcodes.php`. **No React** (that's Stage 3). Keep it **CSS-first**; Stage 3 rebuilds this in React, so don't over-engineer — but the fluid patterns/tokens you set here carry forward.
> Assets are cache-busted via `filemtime` (`shortcodes.php:10-11`) → edits show on a plain reload.
> Bug-ID convention: prefix any findings **`WEB-###`** (you own that namespace); PM holds the canonical log.

## Sprint goal (your part)
Five UX fixes on the live MVP: (1) **home page** matches the cozy-tabletop theme; (2) **game page fits any laptop** with no scrolling; **(3–5) three fixes to the right player drawer** ("My Zone") — move its close button to the right, keep Reactions visible, and show a card's effect on hover. Full plan: `../stage-0.5-plan.md`.

---

## TASK-0.5.1 — Home page → cozy-tabletop theme (Should · 3 SP)

**Problem:** `[mk_home]` still uses the *old* pre-redesign styling with hardcoded off-theme colors, while the lobby/game use the token-based cozy theme.

**Exact locations:**
- Markup: `shortcodes.php:38-66` — `#mk-home.mk-page`, `.mk-actions`, `.mk-join-row`, `#mk-browse-panel`, `#mk-create-panel`, `.mk-create-btns`.
- Off-theme CSS to replace: `style.css:939-953` — `.mk-page { color:#1a1a2e }`, `.mk-btn-primary {#e94560}`, `.mk-btn-secondary {#16213e}`, `#mk-home h1 {#e94560}`, `.mk-join-row input { border:#ccc }`.
- **Model to copy:** `style.css:974-1047` — the `#mk-waiting-room` block already re-themes the same `.mk-btn`/`.mk-page` primitives with tokens. **Do the equivalent, scoped under `#mk-home`.**

**Design tokens (already in `:root`, lines 2-28):** `--bg-table`/`--bg-table-grain`, `--card-paper`/`--card-paper-edge`, `--ink`/`--ink-soft`, `--col-*`, `--gold`/`--gold-d`, `--shadow-1/2/3`, `--radius`/`--radius-l`; fonts Fredoka (headings) + Nunito (body).

**Acceptance Criteria:**
- [ ] Home background uses `--bg-table`(+grain); panels use `--card-paper` + `--radius` + `--shadow-*`
- [ ] Heading in Fredoka; body in Nunito (consistent with lobby/game)
- [ ] Buttons & inputs visually match the lobby (`#mk-waiting-room`) treatment
- [ ] **No hardcoded off-theme colors** (`#e94560`, `#1a1a2e`, `#16213e`, `#ccc`) remain on the home page
- [ ] Looks correct at the existing breakpoints (1280/1024/820) and at mobile width

**Approach:** scope new rules under `#mk-home` (mirrors the lobby's per-page override — lowest risk). *Optional cleaner alternative:* refactor base `.mk-btn`/`.mk-page` to tokens so all pages benefit — but only if you regression-test home + lobby + rules + waiting-room together.

---

## TASK-0.5.2 — Game page fits any laptop (fluid/responsive) (Must · 8 SP)

**Problem:** the game layout is mostly fixed `px` with only `max-width` breakpoints (1280/1024/820) and no vertical scaling, so it **overflows vertically** on short laptops (MacBook Air 13" = 1280×**800**).

**Decided approach: Fluid / responsive CSS** (product-owner choice — not scale-to-fit).

**Layout map** (`shortcodes.php:265-399`, wrapper `#mk-game`): turn bar (`#mk-turn-name`/`#mk-turn-phase` + leave) → `.opps` (`#mk-opps`) → market section (`.market-grid` `#mk-market-low`/`#mk-market-high`) → phase steps + action bar (`#mk-btn-roll`/`#mk-dice-result`/`#mk-btn-skip`) → aside `.drawer` (`#mk-drawer`, body already scrolls). `body:has(#mk-game)` (style.css:35-58) already hides WP chrome + full-bleeds — build on it.

**Step 0 — spike (0.5 SP):** open the play page at 1280×800 in devtools, confirm which region drives the overflow (board vs drawer vs action bar).

**Recipe:**
1. **Fluid root — SCOPED to the game** so it can't break the WP theme/admin: e.g. `body:has(#mk-game) { font-size: clamp(11px, 1vw + 0.3vh, 16px) }`. Convert card/board fixed `px` → `em`/`rem` so they track the root.
2. **Vertical fit:** `#mk-game { height: 100dvh; }` (with an `svh`/`vh` fallback), `display: grid; grid-template-rows: auto auto 1fr auto;` (turn bar / opps / board+market / action bar). Wrapper `overflow: hidden`; inner scroll only where intended (`.drawer-body` already does).
3. **Board/market:** `.market-grid` and player areas → `minmax()` + `fr` columns with `clamp()` gaps so they reflow, not overflow.
4. **Breakpoints:** add **height-based** queries — `@media (max-height: 820px)` and `(max-height: 700px)` — tightening paddings/gaps (the current 3 queries are width-only and miss the MBA case).
5. **Re-fit:** CSS-driven, so resize/orientation re-fits automatically (no JS).

**Acceptance Criteria:**
- [ ] Entire game (turn bar + opponents + market + action bar + drawer) fits with **no vertical or horizontal scroll** at: 1280×800, 1440×900, 1536×864, 1366×768, 1280×720
- [ ] Uses `100dvh`/`svh` (not `100vh`) so browser chrome doesn't cause overflow
- [ ] Nothing clipped; all controls remain clickable
- [ ] Fluid root font is **scoped** to the game (does not affect WP admin/other pages)
- [ ] No regression to home or lobby layouts
- [ ] Re-fits on window resize without reload

---

---

## 🗄️ Tasks 0.5.3–0.5.5 — the right player drawer ("My Zone")

> All three live in the same column — the `aside.drawer#mk-drawer` (`shortcodes.php:329-378`). **Batch them.** Structure inside: `.drawer-toggle` (close btn) → collapsed strip → expanded view → `.drawer-body` (`style.css:615`, scrolls) holding three sections: Landmarks → **My Establishments** (`#mk-my-cards`) → **Reactions** (`#mk-reactions-bar`).

### TASK-0.5.3 — Close button → right of the column (Should · 1 SP)
**Problem:** the drawer's collapse toggle `.drawer-toggle` (`shortcodes.php:330`; CSS `style.css:507-523`) is pinned to the **left** edge (`top:12px; left:-14px;`), floating over the board. Move it to the **right** of the drawer column.
- Change `style.css:507-523`: `left:-14px` → inset right (e.g. `right: 8px; left: auto`). **Don't use a negative `right`** — `#mk-game{overflow:hidden}` (`style.css:98`) will clip it.
- Re-check the rotate-180 on collapse (`style.css:523`) still points the chevron the correct way to re-open.
- AC: right-side, fully visible & clickable, works in expanded **and** collapsed (56px) states, no overlap with coin badge, holds 1280/1024/820 + mobile.

### TASK-0.5.4 — Keep Reactions visible: cap the owned list as a scroll block (Must-usability · 2 SP)
**Problem:** as `#mk-my-cards` (`.owned-grid`, `style.css:686-690`) grows with bought cards, it pushes the **Reactions** section (`shortcodes.php:368-375`) below the fold inside the scrolling `.drawer-body`.
- Give `#mk-my-cards` a `max-height` + `overflow-y:auto` so establishments scroll **internally** and Reactions stay put.
- Match the existing scrollbar thumb style (`style.css:620-621`).
- Respect mobile overrides (`style.css:926-929`) — pick a `max-height` that still shows ≥2 rows on small screens.
- AC: Reactions reachable without scrolling the drawer even with 12+ cards; no clipping; Landmarks section unaffected.

### TASK-0.5.5 — Hover an owned card → show its effect (Should · 2 SP) — depends on 0.5.4
**Problem:** owned cards (`app.js:691-702`) show sym+name+count only; the effect (`state.card_defs[id].effect`) isn't surfaced.
- Minimal: add `title="${esc(card.effect)}"` to the `.owned-card` markup in **`app.js:695`**.
- ⚠️ **Clipping:** if you build a styled tooltip instead, the 0.5.4 `overflow:auto` container will clip a `position:absolute` child. Use native `title`, **or** a `position:fixed` JS tooltip rendered outside the scroll box (`mouseenter`/`mouseleave`).
- AC: hover shows effect text; not clipped by the 0.5.4 scroll block; no layout shift; touch degrades gracefully; keyboard-focus parity if a styled tooltip is used.

---

## Files
- `wp-plugin/machi-koro/assets/style.css` — primary (0.5.1, 0.5.2, 0.5.3, 0.5.4)
- `wp-plugin/machi-koro/includes/shortcodes.php` — minor markup tweaks only if needed
- `wp-plugin/machi-koro/assets/app.js` — **0.5.5** (add `title` / tooltip to `.owned-card`, ~`:695`)

## How to test
Run the stack (`docker compose up -d`), open the play page, use devtools device/responsive mode for the 5 laptop sizes + a short-height profile. Reload picks up CSS automatically (cache-busted).

## Dependencies & DoD
- **No engine dependency** — runs in parallel with Stage 1 (different agent).
- **Internal:** 0.5.5 depends on 0.5.4 (tooltip must escape the new scroll container). 0.5.3/0.5.4/0.5.5 share the drawer — do them together.
- **DoD:** code reviewed · **QA full cross-viewport regression pass** (5 laptop sizes + short-height + lobby/home no-regression) · drawer regression (toggle open/close in expanded **and** collapsed states; Reactions reachable with 12+ cards; hover tooltip not clipped; mobile sizes) · verified in browser · no off-theme colors left on home.
