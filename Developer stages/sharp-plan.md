# Sharp (Millionaire's Row) — Add-on Expansion Plan

> **Status (2026-06-06): PLANNED.** Stage 1, slice 2. Builds on the shipped Base-game slice (`Stage-1_add_base`).
> **Card data:** `MachiKoroCardReference+SHARP.xlsx` + `sprint-2-handoffs/sharp-card-reference.md` (owner-verified).

## Model decision — Sharp is a composable ADD-ON, not a 3rd version
Millionaire's Row is played *on top of* the base game, optionally also with Harbor. So Sharp is an **expansion flag**, not a standalone version:
- Base stays **Basic** or **Harbour** (existing version picker).
- A separate **"+ Sharp"** toggle layers the 13 Millionaire's Row cards onto whichever base.
- Valid combos: Basic, Harbour, **Basic+Sharp**, **Harbour+Sharp** (4 total).
- Config becomes **composable**: `build_config(base, sharp=True)` merges the MR cards onto the base — no `SHARP_GAME` enum, no button explosion, extensible to future add-ons.
- The Sharp mechanics are base-agnostic; the landmark-count conditionals just count constructed landmarks, so they work whether the base has 4 landmarks (Basic) or 6 (Harbour) — for free.

## The 13 cards, by difficulty
**🟢 Tier 1 — fits the existing engine (+ a `landmarks_built` helper):**
Vineyard (7), Corn Field (3–4), General Store (2), French Restaurant (5), Private Club (12–14, take-ALL), Soda Bottling Plant (11, count red across all players).

**🔴 Tier 2 — new mechanics:**
| Card | Dice | Mechanic |
|---|---|---|
| Winery | 9 | Renovation (self-close) |
| Cleaning Company | 8 | Renovation (close a chosen type across all players) + interactive pick |
| Demolition Company | 4 | **Landmark loss** — breaks "landmarks only increase" |
| Tech Startup | 10 | Coins accumulate on the card + "invest" action |
| Park | 11–13 | Redistribute all coins equally |
| Moving Company | 9–10 | Give a non-Major card to another player (interactive) |
| Loan Office | 5–6 | Build-time payout + negative activation |

## Phasing (each phase green & reviewable)
- **Phase A** — config composition (`base + sharp`) + the **6 Tier-1 cards** + `landmarks_built` helper + tests across all 4 combos. *Pure engine/config; no DB/UI yet.*
- **Phase B** — Renovation model (Winery, Cleaning Company): per-card `closed` state.
- **Phase C** — invariant-breakers & interactive cards (Demolition/landmark-loss, Tech Startup/invest, Park, Moving Company, Loan Office).
- **Phase D** — DB `sharp` flag (another `mk_migrate` column) + "+ Sharp" toggle UI + "Base + Sharp" label + **real-browser QA** (the WEB-002 lesson: a protocol bot ≠ a browser).
- **Phase E — Variable Supply (deferred; see below).**

## Phase E — Variable Supply ("10 face-up stacks") — LONG-TERM
The expansions' recommended market variant: instead of every card type being buyable, only **10 distinct types** are on offer; when a type sells out, draw from a shuffled deck until 10 distinct types show again. Solves the Harbour+Sharp board clutter (38 types) and adds market tension.

**Timing — split deliberately:**
- **Engine logic → Stage 1 capstone**, *after* Sharp (Phases A–D) and *after/with* the engine extraction (S1-EXTRACT). It's pure seedable logic (shuffled deck + visible-stack state + refill) and belongs in the clean extracted `machi_koro_engine/`, built once. Behind a `variable_supply` config flag, default-on when Sharp is active. The engine exposes the 10 visible stacks via the existing `state.market`, so the current UI renders it functionally with no rework.
- **Polished market UI → Stage 3 (React rebuild).** The "10 stacks / sold-out reveals a new card" interface is frontend, and the vanilla-JS frontend is replaced by React in Stage 3 — don't build that UI twice.

> Why not sooner: the clutter it solves doesn't exist until Sharp ships, and building it into today's pre-extraction engine (or today's soon-to-be-replaced UI) means doing it twice.

## Risks / open items
- **Test matrix grows to 4 combos** — keep Basic/Harbour green as Sharp is added.
- **Landmark loss (Demolition)** is the one card that breaks a core engine invariant — handle win-check & landmark tracking carefully; it's why it's in Phase C, not A.
- **Interactive prompts** (Cleaning Company type-pick, Demolition landmark-pick, Tech Startup invest, Moving Company give) each need a frontend prompt type — batch them in Phase D.
- Variable supply must use the existing **seedable RNG** for the deck shuffle (deterministic tests).
