# Handoff → Backend Developer · Sprint 1 (Stage 0: Stabilization)

> Paste this into a `backend-developer` Claude session. Work is in `~/Programming projects/Vibe_coding/Claude_Antropic/Machi Koro project`.
> Stack as built: WordPress PHP plugin (`wp-plugin/machi-koro/`) + Python FastAPI WebSocket server (`websocket-server/`) + MySQL + nginx, orchestrated by `docker-compose.yml`.

## Sprint goal
Make the **live** MVP safe for real players: no games lost on restart, no seat impersonation, locked-down REST, and persisted results. You are the primary driver for this sprint.

## Your tasks (do roughly in this order)

### TASK-001 — Persist game state after every action (Must · 8 SP)
**Problem:** `websocket-server/main.py` keeps authoritative state in the in-memory `game_states` dict and only `INSERT`s the *initial* state (`_load_or_create_state`). Per-action changes never reach the DB → a WS restart wipes all live games; reconnection only works while the process lives.

**Do:**
- Add an async helper `save_state(code)` that `UPDATE`s `wp_mk_game_states.state` (JSON) by `table_id`.
- Call it after every `handle_action` result that has `broadcast: True`, and after `_delayed_auto_win` / any finish.
- You'll need `table_id` for each `code` — cache it (e.g. a `code → table_id` dict populated in `_load_or_create_state`) instead of re-querying every action.
- On WS server boot, in-progress games already rehydrate via `_load_or_create_state`; verify a forced restart mid-game restores coins, cards, landmarks, `active_seat`, and `phase`.

**Write-vs-broadcast ordering (decided):** **await the write BEFORE the broadcast** (write-then-broadcast), so state is durable the moment any player can see/act on it. Do *not* fire-and-forget — independent write tasks can land out of order and clobber state, and detached-task exceptions get silently swallowed. Latency is a non-issue (turn-based game, ~1–5ms indexed UPDATE). Debounced writes are over-engineering and widen the crash window. Guardrails: wrap `save_state` so a DB error logs/handles instead of killing the connection loop; keep writes ordered per table (awaiting in the sequential handler gives this for free).

```python
result = handle_action(state, seat, msg)
if result.get('broadcast'):
    await save_state(code)          # persist FIRST
    await broadcast(game_rooms, code, {'event': 'state_update', 'state': state})
```

**AC:**
- [ ] State written to DB after every broadcasting action
- [ ] Forced container restart mid-game preserves full game state
- [ ] Write is awaited before the broadcast; write errors are logged/handled, not swallowed
- [ ] Concurrent actions can't persist state out of order

---

### TASK-002 — Authenticate the game WebSocket (Must · 5 SP)
**Problem:** `game_ws(websocket, code, seat)` accepts any `seat` with no verification — anyone can connect as any player. The plan specified `?token=`.

**Do:**
- WP issues a signed token per (code, seat, identity) — return it from `mk_api_start_game` / `mk_api_join_table`, or add a `/tables/{code}/token` route. Suggest HMAC-SHA256 over `code|seat|identity|exp` using a shared secret.
- Add the secret as an env var to **both** the `wordpress` and `websocket` services in `docker-compose.yml` (e.g. `MK_WS_SECRET`).
- `game_ws` reads the token from the query string, verifies HMAC + expiry + that the seat matches, and closes the socket on failure.
- Actions are only accepted for the socket's authenticated seat (the engine already checks `seat == active_seat`; this hardens *who* the socket is).

**AC:**
- [ ] WP issues a short-lived signed per-seat token
- [ ] WS validates token (signature, expiry, seat/code match); rejects mismatches with a clear close code
- [ ] Expired/invalid token cannot connect or act

---

### TASK-003 — Lock down REST endpoints (Must · 3 SP)
**Problem:** every route in `wp-plugin/machi-koro/includes/api.php` uses `permission_callback => '__return_true'`. Host-only actions (kick/start) lean only on a `host_id` match.

**Do:**
- Verify caller identity server-side for `kick` / `start` / `rename` (host or self via `mk_current_identity()`).
- Add basic rate-limiting on `create_table` per identity (transient counter is fine).
- Validate/normalize all params (codes uppercase + pattern, name length) with consistent `WP_Error` shapes.
- Note: guests authenticate via the spoofable `X-MK-Guest` header — document this limitation; it's acceptable for guests but host actions must match the stored `host_id`.

**AC:**
- [ ] kick/start/rename reject non-authorized callers (403)
- [ ] create_table rate-limited per identity
- [ ] All inputs validated; consistent error responses

---

### TASK-004 — Persist final scores (Must · 5 SP)
**Problem:** `wp_mk_scores` exists (see `includes/db.php`) but nothing writes to it; `calculate_scores()` runs in-memory then is discarded.

**⚠️ Prerequisite gotcha:** the engine's player objects carry only `seat` + `name`, **not `user_id`** (see `create_initial_state`). To attribute scores to registered users you must thread `user_id` through:
- `_load_or_create_state` query already LEFT JOINs `wp_users` — also select `p.user_id` and include it in `players_info`.
- Carry `user_id` onto each player in `create_initial_state` (null for guests).

**Do:**
- When `phase == 'finished'`, write one `wp_mk_scores` row per **registered** player (`user_id NOT NULL`): `landmarks_built`, `coins_at_end`, `won`. Skip guests.
- Make it **idempotent** — guard with a `state['scores_saved'] = True` flag (or check existing rows) so reconnect-triggered finishes don't double-write. This matters because both `check_win` and `_delayed_auto_win` can finish a game.
- A simple leaderboard read (endpoint or WP query) over `wp_mk_scores` for registered users.

**AC:**
- [ ] One score row per registered player on finish; guests skipped
- [ ] No double-writes across both finish paths (win + auto-win)
- [ ] Leaderboard reads from `wp_mk_scores`

---

### TASK-006 (backend half) — Table password protection (Should · 3 SP)
**Problem:** `wp_mk_tables.password_hash` exists but `create_table` never sets it and `join_table` never checks it.

**Do:**
- `create_table` optionally accepts a password → store with `wp_hash_password()`.
- `join_table` requires correct password for protected tables (`wp_check_password()`); wrong → 403.
- Expose an `is_protected` boolean in `list_tables` / `get_table` so the UI can show 🔒. (Web Developer builds the prompt UI — coordinate via PM.)

**AC:**
- [ ] Create stores hashed password when provided
- [ ] Join enforces password on protected tables
- [ ] Table listings expose protected status

---

### Support for QA — deterministic dice hook (part of TASK-005)
`game_engine.py` calls `random.randint(1,6)` directly in several places, which makes the engine untestable. **Provide a seam QA can inject:**
- Add a module-level `_rng = random.Random()` and route every dice roll through it (e.g. `_rng.randint(1,6)`).
- Expose a `seed(n)` helper (or accept an injectable roller) so tests get deterministic rolls.
- This is a small, surgical change — do it early so QA can start TASK-005.

## Dependencies & sequencing
- **001 → 002** are the highest-risk Musts; do them first.
- The **RNG hook unblocks QA's TASK-005** — ship it first if QA is waiting.
- **004** depends on threading `user_id` through state — handle that refactor before writing rows.
- **006 backend** must land before Web can build the prompt UI.

## Definition of Done (every task)
- [ ] Code written & reviewed
- [ ] Tests written (>80% on new logic) — coordinate with QA
- [ ] Deployed to the staging Docker stack
- [ ] README / docs updated for new env vars (e.g. `MK_WS_SECRET`)
