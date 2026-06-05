# Stage 0.5 — Frontend Polish: Theme Consistency + Adaptive Game Fit

> **Status (2026-06-04): CODE-COMPLETE · conditionally closed.** All 5 tasks (0.5.1–0.5.5) implemented by Web-dev and committed on branch `stage-0.5-frontend-polish` (`bdd9e5b`), scoped to the 3 frontend files only. Changes verified in place; PM could not lint (no node/php locally — see Stage-1 carry-forward "PHP-lint in CI").
> **Remaining gate (owner-run, needs a browser):** the full cross-viewport QA regression pass — 5 laptop sizes + short-height + home/lobby no-regression + drawer regression (toggle in expanded **and** collapsed states; Reactions reachable with 12+ cards; hover tooltip not clipped; mobile). Parked alongside the 3 Stage 0 smokes; not blocking Stage 1.

> A small mini-stage between Stage 0 (Stabilize) and Stage 1 (Engine). Pure frontend, **Web-developer owned**. Two UX fixes on the live MVP so it's pleasant to use *now*, before the Stage 3 React rebuild.

## ⚖️ PM trade-off note
This work targets the **current WordPress/vanilla-JS frontend**, which **Stage 3 replaces with React**. So keep it **lightweight and CSS-first** — don't over-invest. The *proper* fully-responsive/mobile layout is a Stage 3 deliverable; Stage 0.5 just makes today's MVP consistent and screen-fitting. No designer agent required (we're applying the existing design language, not creating one).

**Scope:** ~16 SP · Owner: Web · QA: **full** cross-viewport regression pass (fluid approach touches many rules) · Sits before/parallel to Stage 1.

**Task index:**
- 0.5.1 — Home page → cozy-tabletop theme (Should · 3 SP)
- 0.5.2 — Game page fits any laptop (Must · 8 SP)
- 0.5.3 — Move the "My Zone" drawer close button to the right of the column (Should · 1 SP)
- 0.5.4 — Keep Reactions visible: make owned-establishments a fixed scrollable block (Must-usability · 2 SP)
- 0.5.5 — Hover an owned card to show its effect (Should · 2 SP)

> **Tasks 0.5.3–0.5.5 all live in the right-hand player drawer** (`#mk-drawer`). They can ship together in one pass. **0.5.4 and 0.5.5 interact** — see the clipping note in 0.5.5.

---

## TASK-0.5.1 — Restyle the home/landing page to the cozy tabletop theme
**Type:** Feature (UI) · **Priority:** Should · **SP:** 3 · **Assignee:** Web

**As a** player landing on the site
**I want** the home page to look like the lobby and game
**So that** the product feels like one cohesive thing, not two.

> Context: `[mk_home]` (`shortcodes.php:38`) uses generic classes (`mk-page`, `mk-btn`, `mk-actions`, `mk-join-row`, `mk-create-panel`). The theme tokens already exist in `style.css :root`.

**Acceptance Criteria:**
- [ ] Home page uses the existing tokens: `--bg-table`/grain background, `--card-paper` panels, Fredoka headings + Nunito body, `--shadow-*`, `--radius`
- [ ] Buttons & inputs match the lobby/game components (reuse existing `.mk-btn` styling; unify create/browse/join panels)
- [ ] Title treatment consistent with in-game branding
- [ ] No new design language introduced — only existing variables/components
- [ ] Holds up at the existing breakpoints (1280/1024/820) and on mobile width

**Technical notes:** CSS-only where possible; minor markup tweaks in `shortcodes.php` if needed to reuse component classes. No JS changes.

---

## TASK-0.5.2 — Make the game page fit any laptop screen automatically
**Type:** Bug (UX) · **Priority:** Must (usability) · **SP:** 8 · **Assignee:** Web

**As a** player on any laptop
**I want** the whole game board visible without scrolling
**So that** I can actually see and play the game (currently overflows on a MacBook Air 1280×800).

> Root cause: layout is mostly fixed `px` with only `max-width` breakpoints and no `vh`-based vertical scaling. It overflows vertically on short laptop viewports.

**Step 1 — Spike (0.5 SP):** confirm the overflow source — identify the top-level game wrapper and whether the board, side drawer, or log is driving overflow. Pick the approach (see decision below).

**Acceptance Criteria:**
- [ ] Entire game (board + market + player areas + drawer/log) fits within the viewport — **no vertical or horizontal scroll** — on: 1280×800 (MBA 13"), 1440×900, 1536×864, 1366×768, 1280×720
- [ ] Scales down gracefully; nothing clipped, controls stay tappable/clickable
- [ ] Uses dynamic viewport height (`100dvh`/`svh`) so browser chrome doesn't cause overflow
- [ ] No regression to the lobby or home layouts
- [ ] Re-fits on window resize / orientation change without reload

**Decided approach: Fluid / responsive CSS (Option A)** — chosen by product owner for a true responsive foundation (not a uniform scale). Concrete steps:
1. **Root scaling:** set a fluid root font on `html` (e.g. `font-size: clamp(11px, 1vw + 0.3vh, 16px)`) and convert card/board sizing from fixed `px` to `em`/`rem` so everything tracks the root.
2. **Vertical fit:** make the game wrapper `height: 100dvh` (with `svh` fallback) using a grid: `grid-template-rows: auto 1fr auto` (header / board / controls), so the board area absorbs available height and never overflows.
3. **Board/market:** use `minmax()` + `fr` columns and `clamp()` gaps so the market and player areas reflow instead of pushing past the viewport.
4. **Breakpoints:** extend the existing 1280/1024/820 set with at least one short-height query (e.g. `@media (max-height: 820px)`) since the MBA bug is vertical, not horizontal.
5. **Re-fit:** verify on `resize`/orientation without reload (CSS-driven, so automatic).

- ✅ True responsive reflow; readable at all sizes; patterns + dvh/clamp tokens carry forward into the Stage 3 React build
- ⚠️ Touches many fixed-`px` rules → **higher regression risk** → needs the fuller QA cross-viewport pass below
- ⚠️ More effort than scale-to-fit (reflected in the 8 SP)

---

## TASK-0.5.3 — Move the "My Zone" drawer close button to the right of the column
**Type:** Bug (UX) · **Priority:** Should · **SP:** 1 · **Assignee:** Web

**As a** player reading my own stats during the game
**I want** the button that closes my stats column on the right of that column
**So that** collapsing it feels natural and the control isn't floating over the board.

> Context: the right-hand drawer (`#mk-drawer`) **is** the "own stats" column (coins, landmarks, establishments, reactions). Its collapse/expand control is `.drawer-toggle` (`shortcodes.php:330`, styled `style.css:507-523`), currently pinned to the **left** edge of the column (`top:12px; left:-14px;`) where it sticks out over the game board.

**Acceptance Criteria:**
- [ ] The collapse/expand toggle sits on the **right** side of the drawer column (not the left, board-facing edge)
- [ ] Button is fully visible and clickable — **not clipped** by `#mk-game { overflow:hidden }` (`style.css:98`); use an inset offset (e.g. `right: 8px; left: auto`) rather than a negative `right`
- [ ] Still works and reads correctly in the **collapsed** state (`#mk-game.drawer-collapsed`, 56px strip) — the rotate-180 chevron (`style.css:523`) must still point the right way to re-open
- [ ] No overlap with the coin badge / drawer head content
- [ ] Holds at 1280/1024/820 + mobile

**Technical notes:** CSS-only (`style.css:507-523`). Just relocate the absolute position from the left edge to the right, inset. Confirm the rotation direction still communicates open vs. closed after the move.

---

## TASK-0.5.4 — Keep Reactions visible: make owned establishments a fixed scrollable block
**Type:** Bug (UX) · **Priority:** Must (usability) · **SP:** 2 · **Assignee:** Web

**As a** player who has bought several cards
**I want** my establishments list to scroll inside a fixed block
**So that** the Reactions row below it stays put instead of being pushed out of view.

> Root cause: `.drawer-body` (`style.css:615-618`, `flex:1; overflow-y:auto`) stacks three sections — Landmarks → **My Establishments** (`.owned-grid` `#mk-my-cards`, `style.css:686-690`) → **Reactions** (`#mk-reactions-bar`, `shortcodes.php:368-375`). As you buy cards, the owned-grid grows taller and shoves Reactions down below the fold; you have to scroll the whole drawer to reach them.

**Acceptance Criteria:**
- [ ] `#mk-my-cards` has a **capped height** with its **own** internal vertical scroll (e.g. `max-height` + `overflow-y:auto`)
- [ ] The **Reactions** section stays visible without scrolling the drawer, even with a full board of establishments (test ~12+ distinct cards)
- [ ] Scrollbar styling matches the existing drawer-body thumb (`style.css:620-621`)
- [ ] No clipping of card content; counts/names still readable
- [ ] Honors the mobile sizing overrides (`style.css:926-929`) — pick a `max-height` that still shows ≥2 rows on small screens
- [ ] No regression to the Landmarks section above

**Technical notes:** CSS-first on `.owned-grid`. Prefer capping the establishments block over pinning Reactions, but either is acceptable as long as Reactions stay reachable. **Coordinate with 0.5.5** (the hover tooltip must not be clipped by this new scroll container — see below).

---

## TASK-0.5.5 — Hover an owned card to show its effect
**Type:** Feature (UI) · **Priority:** Should · **SP:** 2 · **Assignee:** Web

**As a** player
**I want** to hover one of my owned cards and see what it does
**So that** I can recall a card's function without opening the rules.

> Context: owned cards (`.owned-card`, rendered in `app.js:691-702`) show only symbol + name + ×count — no effect text, unlike market cards which show `.card-effect` inline. The effect string is already available in state as `state.card_defs[id].effect`.

**Acceptance Criteria:**
- [ ] Hovering an owned card surfaces that card's **effect text** (same string the market/rules use)
- [ ] Tooltip is **not clipped** by the 0.5.4 scroll container (`overflow:auto` on `#mk-my-cards`) — use a native `title` attribute (simplest, robust) **or** a JS-positioned `position:fixed` floating tooltip rendered outside the scroll box. A plain CSS `position:absolute` child **will** be clipped — avoid it.
- [ ] Works on keyboard focus too if a styled tooltip is used (a11y); native `title` covers hover by default
- [ ] No layout shift in the drawer on hover
- [ ] Touch devices degrade gracefully (no broken hover-only state)

**Technical notes:** Minimal path = add `title="${esc(card.effect)}"` to the `.owned-card` markup in `app.js:695`. If a styled tooltip is preferred for polish, render it `position:fixed` on `mouseenter`/`mouseleave` (or `pointerenter`) so the 0.5.4 scroll clipping doesn't hide it. **Depends on / coordinate with 0.5.4.**

---

## Sequencing & ownership
- **All five tasks: Web Developer**, can run in parallel with Stage 1 (different agent, no dependency on engine work).
- **0.5.3 / 0.5.4 / 0.5.5 all touch the right drawer** — batch them in one pass. **0.5.5 depends on 0.5.4** (the hover tooltip must escape the new scroll container).
- **QA:** **full** cross-viewport regression pass on 0.5.2 (the 5 laptop sizes + short-height + lobby/home no-regression) + visual check on 0.5.1 + drawer regression for 0.5.3–0.5.5 (toggle open/close in both expanded & collapsed states; Reactions reachable with a full establishment list; hover tooltip not clipped; mobile sizes).
- Not blocking Stage 0 closure; not blocking Stage 1 start.
