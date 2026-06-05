# TASK-101 Spike — Sharp Card Reference & Decision

> **Owner:** Backend (run inline by PM, 2026-06-05) · **Type:** Research spike, no code · **Companion artifact:** `MachiKoroCardReference+SHARP.xlsx` (project root — original sheets + two new Sharp sheets)
> **One-line verdict:** ✅ **KEEP Sharp in Stage 1** — its identity, card list, and mechanics are confirmed enough to build. **But** ~7 of 14 cards have unverified numbers, and Sharp adds genuinely new mechanics that **enlarge TASK-105 and constrain the TASK-103 `GameConfig` design.** Verify the flagged cards before coding.

---

## 1. What "Sharp" is (identity — CONFIRMED, high confidence)
**Sharp = Millionaire's Row.** Wikipedia maps the Japanese release **街コロシャープ (Machi Koro Sharp)** directly to the English **Millionaire's Row** expansion (2015). This is consistent with the project's existing naming, where **Harbour = 街コロプラス (Machi Koro Plus) = the Harbor Expansion** — already in the engine. So the three project versions line up cleanly:

| Project name | Japanese | English product | Status in code |
|---|---|---|---|
| Basic | 街コロ | Machi Koro base | Not yet a config |
| Harbour | 街コロプラス | Harbor Expansion | ✅ implemented (Harbour-only engine) |
| **Sharp** | **街コロシャープ** | **Millionaire's Row** | ❌ this spike |

> The project's own `MachiKoro_FullProductPlan.docx` explicitly deferred this: *"Sharp version — implement ruleset once you have confirmed card list."* There was **no Sharp data anywhere in the repo** (the `xlsx` had only Base + Harbor) — this spike supplies it from the official Pandasaurus rulebook + cross-checked sources.

## 2. Card list (14 establishments, 0 new landmarks)
The **card names and copy counts are CONFIRMED** from the official Pandasaurus "The Expansions" rulebook inventory. Copy count tells us major vs non-major (6× = Blue/Green/Red, 5× = Purple Major). Per-card numbers are confidence-tiered — full table with stable IDs is in the spreadsheet.

**High confidence (build as-is):** General Store, Corn Field, Demolition Company, French Restaurant, Vineyard, Winery, Soda Bottling Plant.
**Medium (verify a number or two):** Private Club, Renovation Company, Tech Startup, Park.
**Low (verify before coding):** Loan Office, Moving Company, Exhibit Hall.

**Landmarks:** Millionaire's Row / Sharp adds **NO new landmarks.** Victory uses the same landmark set as the base config it's layered on (4 base, or 4 + 2 Harbor if combined). It ships renovation tokens + establishments only.

## 3. New mechanics Sharp introduces (the real engine cost — not in Base/Harbour)
This is the headline for sizing. Sharp is **not** "Harbour + more cards" — it adds mechanics the current engine has no concept of:

| Mechanic | What it does | Engine impact |
|---|---|---|
| **Renovation** | A card can be *closed* (token); skips its next activation, then reopens. Winery self-closes; Renovation Company closes a chosen type across **all** players. | New per-card `closed` state; activation checks/consumes the token instead of paying. |
| **Landmark loss** | Demolition Company turns one of your built landmarks face-down for +8 coins. | ⚠ Breaks the **"landmarks only increase"** invariant the engine + win-check rely on. Landmarks can now go built→unbuilt. |
| **Landmark-count conditionals** | Corn Field/General Store fire only if owner has <2 landmarks; French Restaurant needs roller 2+; Private Club needs roller 3+. | Needs a "count constructed landmarks (excl. City Hall)" helper at activation time. |
| **Accumulated card state** | Tech Startup accumulates invested coins on the card across turns. | New persistent per-card counter + a distinct "invest" action. |
| **Coin redistribution** | Park pools all players' coins and splits equally. | Whole-table coin op; define rounding (verify). |
| **Take-all** | Private Club takes ALL of the active player's coins. | Unbounded steal; clamp at balance. |

## 4. Discrepancies found across sources
- **Winery cost:** official rulebook art shows **3**; one secondary source said 2. Using **3**, flagged.
- **Park classification:** official copy-count (5×) makes it a **Major (Purple)**; one fan source listed it Green w/ dice 11–13. Treating as Major per the rulebook; dice unverified.
- **Soda Bottling Plant scope:** "red cards owned by **all players**" vs "by **you**" — sources disagree; verify.
- **Private Club:** renamed from "Member's Only Club" in the 5th-Anniversary edition; cost not found.
- **Exhibit Hall:** effect text only partially captured from the rulebook image; treat effect as unconfirmed.

## 5. Decision & recommendation
**✅ Confirmed enough to KEEP Sharp in Stage 1 (per owner's instruction), with two conditions:**

1. **Verify the flagged cards before TASK-105 codes them.** Owner action — check a physical Millionaire's Row deck or a definitive card database for: Private Club (cost), Loan Office (dice/type/cost), Moving Company (dice/cost), Exhibit Hall (effect/dice/cost), Park (dice), Soda Bottling Plant (scope), Winery (cost 2 vs 3). ~7 cards. Everything else is build-ready.
2. **Re-sequence the GameConfig design to absorb Sharp's mechanics.** The new mechanics mean **TASK-103 (`GameConfig`) must support per-card mutable state, rule toggles (renovation, invest), and landmark-loss** — not just a static card list. And **TASK-105 (Sharp config) is bigger than its placeholder 8 SP**; recommend re-estimating after the verification pass — provisionally **8 → 13 SP**, with renovation + landmark-loss as the cost drivers.

**Why not descope:** identity, full name list, copy counts, and the renovation mechanic are all confirmed from the official rulebook, and 7 cards are fully build-ready today. The unknowns are a handful of numbers, not a missing product — descoping isn't warranted. The honest risk is **complexity/sizing**, not feasibility.

## 6. Open questions for the owner
1. Confirm the 7 flagged card specs (§4 list above) — or point me at your physical deck / preferred source and I'll finalize the table.
2. **Design call for TASK-103:** should Sharp's landmark-loss (Demolition Company) be in scope for Stage 1, or do we ship Sharp *without* Demolition Company first (it's the one card that breaks a core engine invariant)? This materially affects TASK-103's design and TASK-105's size.
3. Confirm we're targeting the **5th-Anniversary "The Expansions" (2019)** card text as canonical (that's the rulebook this spike used), vs. the original 2015 printing — a few names/numbers differ between printings.

---
*Sources: official Pandasaurus "Machi Koro: The Expansions" rulebook (boardgame.bg), en.wikipedia.org/wiki/Machi_Koro, machi-koro.fandom.com (French Restaurant / General Store / Soda Bottling Plant / Demolition Company / Member's Only Club entries via search), variablepig.org Machi Koro expansion rules. Effect text reconciled across these; numbers tiered by agreement.*
