# Sprint 1 — Staging Deployment / Sign-off Checklist

> Several tasks changed schema (`db.php`) or env (`docker-compose.yml`). Those only take effect on redeploy — code being correct is **not** sufficient. Run this on staging before signing off the affected tasks. Owner: Backend deploys, QA verifies, PM signs off.

## Why this exists
- `db.php` schema changes apply only when `dbDelta` re-runs → **plugin must be re-activated**.
- `dbDelta` **silently fails to add a UNIQUE index** if the table already holds rows that violate it (pre-existing duplicates).
- `docker-compose.yml` env changes (e.g. `MK_WS_SECRET`) apply only when containers are **recreated**, not just restarted.

> ### ⚠️ QA-008 — rebuild the websocket image when `websocket-server/` changes
> The **WP plugin is bind-mounted** (edits go live immediately), but the **`websocket` service is a built image** — the Python code is baked in at build time, **not** mounted. So `docker compose up -d` alone will silently run **stale** engine code. Any change under `websocket-server/` (engine, configs, `main.py`) requires:
> ```
> docker compose build websocket && docker compose up -d websocket
> ```
> **Symptom if skipped:** a Basic table silently builds a full Harbour game with `state.version = null` (exactly how QA caught this on B4). Treat "did the websocket image get rebuilt?" as the first question whenever engine behavior looks like a previous version.

## Checklist

### QA-001 — `mk_game_states` UNIQUE(table_id)  [gates TASK-001 final sign-off]
- [ ] Plugin re-activated on staging (migration ran)
- [ ] No pre-existing duplicates: `SELECT table_id, COUNT(*) FROM wp_mk_game_states GROUP BY table_id HAVING COUNT(*) > 1;` → **zero rows** (if not zero, de-dupe or drop/recreate the table first — MVP data is disposable)
- [ ] Index present: `SHOW INDEX FROM wp_mk_game_states` lists the `table_id` unique key
- [ ] **Fallback if dbDelta didn't add it:** explicit `ALTER TABLE wp_mk_game_states ADD UNIQUE KEY uq_table_id (table_id);`

### TASK-002/003 — new identity column + env  [gates TASK-002/003 final sign-off]
- [ ] Plugin re-activated → new identity column exists (`SHOW COLUMNS FROM …`)
- [ ] `MK_WS_SECRET` present in **both** `wordpress` and `websocket` services after `docker compose up -d` (recreate, not restart); values match
- [ ] Registered-host action works end-to-end (ties to VERIFY-001 nonce check)

### TASK-004 — scores  [gates TASK-004 final sign-off]
- [ ] Re-activation applied the new `wp_mk_scores.game_seq` column (`SHOW COLUMNS FROM wp_mk_scores`) — QA-006 fix
- [ ] `UNIQUE KEY (table_id, game_seq, user_id)` present (`SHOW INDEX FROM wp_mk_scores`) — QA-006/QA-007 (mind the pre-existing-duplicate caveat: de-dupe first if needed)
- [ ] Score row written for a registered player on a real finished game; none for guests
- [ ] **Rematch test:** play 2 games at the same table → both games' scores persist (one set of rows per `game_seq`)

### TASK-006 — passwords (no migration; `password_hash` column pre-existed)
- [ ] Create with/without password → `is_protected` reflects it in **list + detail**
- [ ] Join protected table: wrong password → 403 (modal retries); correct → seat + token
- [ ] Raw `GET /tables/{code}` body contains **no** `password_hash` / `host_id` keys (WEB-001)

### Cross-cutting code quality (VERIFY-002)
- [x] PHP-lint step added to CI — `.github/workflows/php-ci.yml` `php-lint` job runs `php -l` across all plugin PHP on every push (TASK-108 / CI-1). The manual `php -l` staging check is now a backstop, not the first line.
- [x] CI also boots WordPress on a MySQL service and verifies the schema bootstrap + migration (`migration` job) — closes the DEPLOY-001 manual-sweep gap.

### B4 — game_version on `wp_mk_tables`  [gates B4 final sign-off]
- [ ] Re-activation / `plugins_loaded` applied the new `game_version` column (`SHOW COLUMNS FROM wp_mk_tables LIKE 'game_version'`) — added by explicit migration `mk_migrate()`, NOT dbDelta (see `sprint-2-handoffs/migration-discipline.md`)
- [ ] Existing pre-B4 rows backfilled to `'harbour'` (default) → unchanged behavior
- [ ] Create a **Basic** table and a **Harbour** table → each starts the right game (Basic: 15 cards, 4 landmarks, no City Hall; Harbour: as today)
- [ ] `game_version` round-trips: value chosen at create is what the websocket-server reads when the game starts

> Negative-gate demonstration (retro #2 DoD): on a throwaway branch, introduce a PHP syntax error or a broken `ALTER` and confirm `php-ci` goes **red**, then revert to green.

## Sign-off rule
A task is **Done** only when: code reviewed ✅ + tests green in CI ✅ + **this checklist's items for that task pass on staging** ✅.
