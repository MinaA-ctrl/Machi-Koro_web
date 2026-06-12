# Stage 3 — WebSocket Event & Animation Contract (Backend ⇄ Frontend)

> **Status (2026-06-12): PROPOSED — engine + WS implemented, awaiting web-dev sign-off.**
> The contract the React frontend (S3.3/S3.4/S3.5) builds its animations and
> interactive prompts against. **Additive to Stage 2** — engine *rules* are
> unchanged; this exposes existing truth at finer granularity and adds the
> prompt request/response loop. **Server stays authoritative; the frontend is a
> pure view** — it animates over the events below and never computes outcomes.
>
> **Implemented in:** `machi_koro_engine/events.py` (keyed-event vocabulary + EN
> renderers), `machi_koro_engine/game_engine.py` (emits + prompt helpers),
> `app/ws.py` (broadcast wiring, structured prompts, timeout, reconnect).
> **Tests:** `machi_koro_engine/tests/test_events.py` (18, engine-pure),
> `app/tests/test_ws_game.py` (+4 WS-layer). **All 200 engine tests green.**
>
> **Coordination:** web-developer — please review §4 (prompt request/response) and
> §6 (event vocabulary) before building the animations. The schema is meant to be
> agreed **once**; ping back any field you need added rather than diffing state.

---

## 1. Principles

1. **Server-authoritative.** Every die value, coin movement, market change, and
   prompt resolution is decided by the engine. The frontend plays the *visual*
   (idle→tumble→result, coins flying, slot flip) and then renders the truth.
2. **Granular, not derived.** The backend sends explicit deltas (which card
   activated, who paid whom, which slot emptied and what replaced it). The UI
   never diffs full state to infer what happened.
3. **Keyed for i18n.** Player-facing text is a `{type, params}` event, not an
   English string. The frontend localizes EN/RU from the key + params.
4. **Additive / back-compatible.** All Stage-2 messages still fire unchanged, so
   the live WP-JS UI keeps working during the strangler-fig cutover. The new UI
   consumes the two new message types (`game_events`, `game_prompt`) and may
   ignore the legacy `prompt` / `coin_event` / `game_toast` text messages.

## 2. Channels (unchanged from Stage 2)

| Channel | Endpoint | Auth |
|---|---|---|
| Lobby | `WS /ws/{code}/lobby/{seat}` | none (as today) |
| Game  | `WS /ws/{code}/game/{seat}?token=…` | per-seat WS token; bad/missing/wrong-seat → close **4401** |

The game socket sends a full `state_update` snapshot immediately on (re)connect.

## 3. Server → client messages

| `event` | New? | Audience | Purpose |
|---|---|---|---|
| `state_update` | legacy | all | Authoritative full state snapshot (`{event, state, connected_count}`). The **truth**; sent after every mutating action and on connect. |
| **`game_events`** | **NEW** | all | The ordered keyed-event **delta** produced by the last action — the animation script (§5,§6). `{event, events:[…]}`. |
| **`game_prompt`** | **NEW** | active player | Structured interactive prompt (§4). `{event, promptId, type, active_seat, params, options, response_event, default, timeout_seconds, text}`. |
| `prompt` | legacy | active player | Old yes/no prompt (harbor/reroll only): `{event, text, promptId}`. Kept for the WP-JS UI; new UI uses `game_prompt`. |
| `game_toast` | legacy | all | English toast (announces + transfers). Superseded by `game_events` for the new UI. |
| `coin_event` | legacy | per-seat | English coin-delta strings. Superseded by the payout events in `game_events`. |
| `reaction` | legacy | all | Emoji reaction `{seat, emoji}`. |
| `player_joined`/`player_left`/`table_closed` | legacy | lobby | Lobby lifecycle. |
| `player_rejoined_game`/`player_left_game` | legacy | game | Presence. |

**The new UI needs exactly: `state_update` (truth) + `game_events` (animation) +
`game_prompt` (interaction).** Everything else is legacy/optional.

## 4. Interactive prompts — request/response loop (Deliverable 4)

When the engine needs a decision from the active player it sets
`state.pending_prompt` and the server pushes a **`game_prompt`** to that player's
socket. The player replies with a client→server message; the server **validates,
applies, and broadcasts** the result (a new `state_update` + `game_events`). If
the player doesn't reply within `timeout_seconds`, the server **auto-applies the
`default`** so the game can't stall.

### 4.1 `game_prompt` payload

```jsonc
{
  "event": "game_prompt",
  "promptId": "cleaning_company",     // == type; stable per prompt kind
  "type": "cleaning_company",
  "active_seat": 0,                    // who must respond
  "params": { … },                    // data to render the choice (localized on FE)
  "options": [ … ] | { … },           // the legal choices (see per-type below)
  "response_event": "cleaning_company_pick",  // the event the FE sends back
  "default": { "event": "…", … },     // auto-applied on timeout (always valid)
  "timeout_seconds": 45,              // server auto-resolves after this
  "text": "Cleaning Company: pick a type to close board-wide."  // EN fallback only
}
```

`text` is an **English fallback** — the frontend should render its own localized
string from `type` + `params` and use `text` only as a safety net.

### 4.2 The four Sharp prompts

| Prompt (`type`) | `params` | `response_event` → fields | Default (timeout) |
|---|---|---|---|
| **Cleaning Company** *(pick a card type)* | `{targets:[card_id]}` — non-Major types with an open copy on the board | `cleaning_company_pick` → `{card_type}` | first target |
| **Demolition** *(pick a landmark)* | `{targets:[landmark_id], remaining}` — own built, non-City-Hall landmarks | `demolition_pick` → `{landmark_id}` | first target |
| **Moving Company** *(give a card to a player)* | `{giveable:[card_id], targets:[seat], remaining}` | `moving_company_pick` → `{card_id, target_seat}` | first giveable → first target |
| **Tech Startup** *(invest amount)* | — *not a prompt* (see note) | `tech_startup_invest` → `{}` (invest 1) | — |

> **Tech Startup is not a server prompt.** Per the engine, investing is an
> *optional* build-window action — move **1 coin** onto the card, **≤ once per
> turn** (`tech_invest_used`), total persists. The frontend renders an "Invest 1🪙"
> button during the active player's build phase when they own Tech Startup and have
> ≥1 coin; it sends `{"event":"tech_startup_invest"}`. There is no timeout because
> "don't invest" is the natural default. Each accepted invest emits a
> `tech_invest` event (so the UI can animate the coin landing + the running total).

### 4.3 The other (non-Sharp) prompts, same envelope

| `type` | `params` | `response_event` → fields | Default |
|---|---|---|---|
| `harbor_bonus` | `{roll, total_with_bonus}` | `prompt_response` → `{answer:bool}` | `{answer:false}` (keep roll) |
| `reroll` (Radio Tower) | `{roll}` | `prompt_response` → `{answer:bool}` | `{answer:false}` (keep roll) |
| `tv_station` | `{opponents:[{seat,name,coins}]}` | `tv_station_pick` → `{target_seat}` | richest opponent |
| `business_center` | `{my_cards:[card_id], opponents:[{seat,name,cards:[card_id]}]}` | `business_center` → `{my_card, opp_seat, opp_card}` **or** `skip_business_center` | skip |
| `tuna_roll` | `{tuna_seats:[seat]}` | `tuna_roll` → `{}` | auto-roll |

### 4.4 Validation, timeout, reconnection

- **Validation:** every response is validated server-side exactly as a human's
  (wrong turn, illegal target, insufficient coins → ignored, no state change). The
  `default` is always a guaranteed-valid move.
- **Timeout:** `timeout_seconds` (default `PROMPT_TIMEOUT_SECONDS = 45`). On
  expiry the server applies `default` on behalf of the active player and
  broadcasts the result. A response that arrives first cancels the timer; a
  chained prompt (e.g. multi-copy Demolition) re-arms a fresh timer.
- **Reconnection:** on (re)connect the player gets the `state_update` snapshot; if
  they are the **active player and a prompt is outstanding**, the server **re-emits
  `game_prompt`** so the modal reappears. The original timeout keeps running, so a
  dropped player never stalls the table — they simply regain the choice if they
  return in time. `pending_prompt` is also in `state`, so the UI can render the
  prompt from the snapshot alone if it prefers.

## 5. Ordering & sequencing guarantees

- Every event carries a **monotonic `seq`** (per game, increasing, never reused).
  **Order animations by `seq`**, and use it to **dedupe** across reconnects.
- Per action the server emits, in this wire order:
  **1)** `state_update` (final truth) → **2)** `game_events` (the transition's
  ordered events) → **3)** legacy toasts/coin_event → **4)** legacy `prompt` →
  **5)** `game_prompt`.
- **Recommended frontend pattern:** keep showing the *prior* board, play the
  `game_events` script in `seq` order (dice tumble → settle on `roll.total`; then
  each payout's coins fly per `seq`; then market flip), and reconcile against the
  already-received `state_update` at the end. Because the truth is already in hand,
  animations are pure decoration and can be **skipped instantly** (honor
  `prefers-reduced-motion` by snapping to `state_update`).
- Multiple payouts from one roll arrive as **separate, ordered** payout events
  (e.g. two opponents' cafés → two `take` events) so coins sequence one-by-one.

## 6. Keyed event vocabulary (`game_events[].t`)

All events are `{t, seq, …params}`. **Names** are localized on the frontend from
`card_id` / `landmark_id` / `seat`-`name`; `source` is a card **or** landmark id.

### Dice (Deliverable 1)
| `t` | params | notes |
|---|---|---|
| `roll` | `seat,name,dice:[…],total,doubles,dice_count` | `dice_count` 1 **or** 2 → one- vs two-die mode is in the event. Animate idle→tumble→`total`. |
| `reroll` | `seat,name,dice,total,doubles,dice_count` | Radio Tower reroll. |

### Coin payout stream (Deliverable 2) — `t ∈ PAYOUT_TYPES`, animate coins by `seq`
| `t` | params | flow |
|---|---|---|
| `income` | `seat,name,amount,source` | **bank → player** |
| `take` | `taker_seat,taker_name,payer_seat,payer_name,amount,source` | **player → player** (red restaurants, Stadium, Publisher, Tax Office, Tech Startup payout, TV Station) |
| `bank_pay` | `seat,name,amount,source` | **player → bank** (Loan Office activation) |
| `tuna_payout` | `seat,name,amount,dice:[a,b],total` | bank → player, after the Tuna 2-die roll |
| `city_hall` | `seat,name` | bank → player, +1 safety net at 0 coins |
| `park_split` | `seat,name,deltas:[{seat,name,before,after,delta}]` | Park pools & redistributes — per-player deltas for the animation |

> **Bank vs player-vs-player is explicit:** `income`/`bank_pay`/`tuna_payout`/
> `city_hall` involve the bank; `take` is strictly player↔player (it carries both
> `payer_*` and `taker_*`). `source` tells you the card/landmark to badge.

### Market reveal (Deliverable 3)
| `t` | params | notes |
|---|---|---|
| `market_reveal` | `bought_card_id, slot_emptied:true, revealed:[card_id], supply:{card_id:count}` | **Variable-Supply only.** Fires when a purchase empties a stack: animate **buy → empty → reveal** of `revealed` (the new face-up type(s)). `supply` is the authoritative post-refill face-up counts. Classic supply emits nothing. |

### Build / market
| `t` | params |
|---|---|
| `buy_card` | `seat,name,card_id` |
| `buy_landmark` | `seat,name,landmark_id` |
| `loan_build` | `seat,name` (Loan Office build-time +5) |

### Sharp / interactive resolutions
| `t` | params |
|---|---|
| `cleaning` | `seat,name,card_id,count` |
| `tech_invest` | `seat,name,total` |
| `demolish` | `seat,name,landmark_id` |
| `moving_give` | `seat,name,card_id,target_seat,target_name` |
| `trade` | `seat,name,card_id,opp_seat,opp_name,opp_card_id` (Business Center) |
| `renovation_reopen` | `seat,name,card_id` |
| `renovation_close` | `seat,name,card_id` (Winery) |
| `tuna_announce` | `seats:[…],names:[…]` |

### Turn / meta + toast-only
| `t` | params | logged? |
|---|---|---|
| `amusement_park` | `seat,name` | yes |
| `win` | `seat,name` | yes |
| `win_forfeit` | `seat,name` | yes (all others left) |
| `no_income` | — | toast-only |
| `bc_offer` | `seat,name` | toast-only |
| `trade_done` | `seat,name,card_id,opp_seat,opp_name,opp_card_id` | toast-only |
| `skip_build` | `seat,name` | toast-only |

> **`TOAST_ONLY`** (`no_income, bc_offer, trade_done, skip_build, market_reveal`)
> never produced a legacy `state.log` line; everything else does. `state.log`
> stays English and is now **fully derived** from the non-toast events
> (`render_en`), so the legacy UI is byte-identical while the new UI localizes
> from the keys.

## 7. i18n (Deliverable 5)

- The engine no longer hard-codes player-facing prose: every `add_log` site is now
  `emit(state, <type>, **params)`. `state.log` is the EN render of those events;
  the new UI ignores `log`/`text` and renders from `t` + `params`.
- **Frontend catalog keys:** one message key per `t` (the **game log**), plus one
  per `promptId` (**prompt text**). Card and landmark display names come from the
  frontend's own catalogs keyed by `card_id` / `landmark_id`; **player names are
  data, not translated.** RU is ~30% longer — size log rows / prompt modals to grow.
- **Behavior-identical:** the 182 pre-existing engine tests stay green; `test_events.py`
  asserts `state.log == [render_en(e) for non-toast events][-15:]`, locking the
  derivation.

## 8. Client → server message reference

| `event` | fields | when |
|---|---|---|
| `roll` | `{dice_count:1|2}` | active player's roll phase (2 needs Train Station) |
| `prompt_response` | `{answer:bool}` | harbor_bonus / reroll |
| `tv_station_pick` | `{target_seat}` | tv_station |
| `cleaning_company_pick` | `{card_type}` | cleaning_company |
| `demolition_pick` | `{landmark_id}` | demolition |
| `moving_company_pick` | `{card_id, target_seat}` | moving_company |
| `business_center` / `skip_business_center` | `{my_card,opp_seat,opp_card}` / `{}` | business_center |
| `tech_startup_invest` | `{}` | build phase, optional |
| `tuna_roll` | `{}` | tuna_roll |
| `build` | `{type:"card"|"landmark", id}` | build phase |
| `skip_build` | `{}` | build phase |
| `new_game` | `{}` | finished (≥2 connected → rematch) |
| `reaction` | `{emoji}` | any time |

All are ignored unless they come from the **active seat in the matching phase**
(except `reaction`, which is presence-only). Unknown/illegal → no-op, no state change.

## 9. Versioning & back-compat

- No existing message changed shape. Two state keys were **added** (`events`,
  `event_seq`) — generic JSON persistence round-trips them; restart-survival and
  rematch (`game_seq`) are unaffected.
- New event types are additive: the frontend must **ignore unknown `t`** so the
  backend can extend the vocabulary (e.g. future expansions) without a lockstep
  release.

## 10. Open coordination points (for web-developer)

1. **Reduced-motion:** confirm the FE snaps to `state_update` and skips the
   `game_events` script under `prefers-reduced-motion` (a11y, S3.7).
2. **Prompt timeout UX:** 45s server-side. Do you want a visible countdown? If so,
   read `timeout_seconds` from `game_prompt` (don't hard-code).
3. **Market reveal on mobile:** the `market_reveal.revealed` list may contain **>1**
   card (a drawn duplicate stacks without filling a slot, so the deal continues to
   the next new type). The mobile carousel must handle a multi-card reveal.
4. **Park animation:** `park_split.deltas` gives every player's before/after — use
   it to animate the pool→redistribute, not N separate payouts.
