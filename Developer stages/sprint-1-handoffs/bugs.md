# Sprint 1 — Bug Log (canonical)

## Bug-ID convention (adopted Sprint 1)
- **Each agent prefixes its own findings by area:** `BE-001`, `QA-001`, `WEB-001`, incrementing within its own namespace.
- **Prefix = FINDER (who first files it), not who fixes it.** A fix *references* the existing ID; it never mints a new one. (So a QA-found bug fixed by Backend stays `QA-###`.)
- **PM owns this master log** and never renumbers — just records. Namespaces can't collide, so no reconciliation hop.
- **PM never mints IDs in an agent's namespace** (the agent's own counter would collide with it). Items the PM formalizes that no agent numbered — or cross-cutting/coordination items — get a **`PM-`** prefix. `VERIFY-` is used for verification-only items.
- Agents reference bugs by prefixed ID in handoffs, commits, and re-verify loops.

> Remap from the old flat `BUG-NNN` scheme: QA-origin BUG-001/002/003 → QA-001/002/003; seat-reuse (old BUG-005) → QA-004; rate-limit (old BUG-006) → QA-005; kick-guard (old BUG-007) → PM-001 (relabeled out of QA's namespace, see below); password leak (old BUG-004, Web-origin) → WEB-001.

---

## TASK-001 — Persistence ✅ (DoD closure: regression tests delivered under TASK-005)

### QA-001 · High · P0 · FIXED (verified; regression: TASK-005 concurrent-reconnect TC)
Duplicate `wp_mk_game_states` rows from check-then-INSERT race (no UNIQUE on `table_id`). Fixed: `UNIQUE KEY (table_id)` + `INSERT … ON DUPLICATE KEY UPDATE` + per-`code` `asyncio.Lock`. PRD already specified `table_id` UNIQUE — restores intended invariant.

### QA-002 · Medium · P1 · FIXED (verified; regression: TASK-005 action-vs-auto-win TC)
`_delayed_auto_win` detached task → unordered write / swallowed exceptions. Fixed: phase re-check before write, terminal finished-state, `add_done_callback`.

### QA-003 · Low · P2 · FIXED (verified)
`save_state` silently no-ops on missing `table_id`. Fixed: log line before return.

## TASK-002 — WS auth ✅

### QA-004 · Medium · P1 · FIXED (verified via HMAC interop harness + repro)
Seat collision: `mk_api_join_table` allocated seats by `COUNT(*)` → after a kick, a new joiner could reuse a live seat, yielding two valid tokens for one seat. Fixed: seat = `COALESCE(MAX(seat),-1)+1` (`api.php:118-121`); token signed for same seat; full-table guard stays count-based. Intended side effect: seats can be non-contiguous after kicks (e.g. {0,5,6}) → engine must address by seat value, not index (proven by TASK-005 non-contiguous-seat TC).
- Backend updated the in-code comment `BUG-005` → `QA-004`. ✅

## TASK-003 — REST lockdown (auth + validation ACs accepted; rate-limit fast-follow)

### QA-005 · Medium · P2 · FIXED (code; ⏸️ pending staging verify)
`create_table` rate-limit bypassable — a guest omitting/rotating `X-MK-Guest` gets a fresh `guest:uniqid()` identity per call. Fixed: `mk_client_ip()` (trusts nginx `X-Real-IP`, validated via `FILTER_VALIDATE_IP`) + `mk_rate_limit_key()` → `user:<id>` for logged-in, `ip:<client>` for anonymous; throttle keys on that, not the rotatable identity. Throttling-only control (IP rotation is a far higher bar than header rotation). MVP limitation (non-atomic read-modify-write) carried forward, documented.

### PM-001 · Low · OPEN (QA-surfaced; relabeled from a mis-minted "QA-006")
`mk_api_kick_player` has no `status='waiting'` guard (`api.php:163`) → host can delete a `wp_mk_players` row mid-game, corrupting the roster TASK-004 reads for scores. Fix: add `AND status='waiting'`. **Status: FIXED — folded into the QA-006 patch.**

### Accepted MVP limitations (no action)
- Rate-limit is read-modify-write, not atomic (`get_transient`/`set_transient`) — may slightly over-admit under concurrency. Acceptable for MVP; documented in the docstring.

## TASK-004 — Scores ✅ (QA-verified; ⏸️ staging migration check on `wp_mk_scores`)

### QA-006 · Medium-High · P1 · FIXED + VERIFIED (QA: Python flow + sqlite upsert replay — rematch persists, re-finish idempotent)
**Rematch (`new_game`) scores silently lost for every game after the first.** The DB idempotency guard keys only on `table_id` (`save_scores`), but `new_game` reuses the same `table_id`. So game 2's `save_scores` sees game 1's rows → sets `scores_saved=True` → skips the INSERT. Silent data loss on a first-class flow.
- **Fix (unified with QA-007):** per-game discriminator `state['game_seq']` (0 init; increment in `new_game`; persist via `save_state`) + `wp_mk_scores.game_seq` column + `UNIQUE KEY (table_id, game_seq, user_id)` + **`INSERT … ON DUPLICATE KEY UPDATE`** (atomic upsert chosen over a COUNT guard — closes re-finishes, restart flag-loss, and concurrent replicas in one mechanism; in-memory flag stays as fast path). PM-001 folded into this pass.

### QA-007 · Low · FIXED + VERIFIED (UNIQUE key proven idempotent on sqlite replay)
**`wp_mk_scores` has no UNIQUE constraint** — idempotency is app-level only (COUNT-then-INSERT). Safe under single container + per-code lock, but two WS replicas could both COUNT 0 and both INSERT. The `UNIQUE KEY (table_id, game_seq, user_id)` from the QA-006 fix closes this too.

> Verified-good in TASK-004: `user_id` threaded cleanly (engine + `_load_or_create_state`); dual idempotency (in-memory flag + DB guard); flag persisted in the snapshot; guest-only games write zero rows; leaderboard aggregates per registered user. Only the rematch discriminator is missing.

## TASK-006 — Table passwords

### WEB-001 · Medium · P1 · FIXED (code; ⏸️ pending QA verify: raw GET body has no `password_hash`/`host_id`)
`mk_api_get_table()` returns `t.*` → leaks `password_hash` (and `host_id`) to the client. Public endpoint. Fix: drop `password_hash`/`host_id` from the SELECT; return `is_protected` (= `password_hash IS NOT NULL`). Folds into TASK-006 backend + the TASK-003 lockdown. See `task-006-contract.md`.

## Cross-cutting verification

### VERIFY-001 · CODE-VERIFIED PASS (⏸️ staging E2E smoke, low-risk)
PM checked: `shortcodes.php:16` localizes `MK.nonce = wp_create_nonce('wp_rest')`; `app.js` sends `X-WP-Nonce: MK.nonce` on every request. Nonce IS sent → registered hosts resolve correctly; the silent-host-as-guest failure does not exist in code. Remaining: a staging smoke that a logged-in host can start/kick.
Original concern:
Confirm `app.js` sends `X-WP-Nonce` on registered-host REST actions (create/start/kick/rename). Without it, `get_current_user_id()` returns 0 → a logged-in host is treated as a guest and host-matching silently fails. Side benefit if present: CSRF mitigation.

### VERIFY-002 · OPEN — PHP lint never run on `api.php`
Standing gap flagged by Backend across all `api.php` work (TASK-002/003/004/006): no `php -l` has run (no PHP binary locally; CI installs only pytest). A syntax slip would only surface at runtime on staging. **Action:** run `php -l api.php` on staging; add a PHP-lint step to CI (Stage 1 hardening at the latest).

### DEPLOY-001 · High · RESOLVED — dropped+recreated mk_ tables; schema now matches code (UNIQUE table_id ✅, game_seq + uniq_score ✅, zero dups)
Staging sweep found the live DB doesn't match `db.php` (which is correct). `wp_mk_game_states` has no UNIQUE on `table_id` (QA-001 not live → P0 still exploitable here); `wp_mk_scores` has no `game_seq` column or `uniq_score` key (scores INSERT would error). Cause: plugin not re-activated AND 37+ pre-existing duplicate rows in `wp_mk_game_states` block the UNIQUE index. PHP lint (VERIFY-002) ✅ all 4 files clean.
- **Remediation (disposable MVP data): drop the `mk_` tables → re-activate plugin → recreate fresh from `db.php`.** Then re-verify SHOW INDEX/COLUMNS + dup check = 0.
- Lesson: `dbDelta` won't add a UNIQUE index over existing duplicates, and doesn't reliably alter indexes — fresh recreate or explicit ALTER required on dirty tables.

### Deferred / backlog
- No connection pooling — `save_state` opens a fresh `aiomysql.connect()` per action. → **Stage 1** (FastAPI/SQLAlchemy pool). Tech debt.
- Reconnect cosmetic — first reconnecting player after restart misses `player_rejoined_game`. → Low-pri polish.
