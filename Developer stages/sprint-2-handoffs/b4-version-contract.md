# B4 — Game Version Selection Contract (Basic / Harbour)

> Shared interface between Backend (api.php, websocket-server) and Web (app.js, B5).
> Backend is built to this; the frontend version picker (B5) conforms to it.

## The field

- **Name:** `game_version`
- **Type:** string
- **Allowed values:** `"basic"` | `"harbour"` (lowercase keys)
- **Default:** `"harbour"` (current live behavior; chosen when omitted)
- **Display names** (what the engine puts in game state, for labels):
  `basic → "Basic"`, `harbour → "Harbour"`.

Validation is **defensive on every layer**: an unknown/missing value falls back
to `harbour` rather than erroring. The frontend should still only ever send
`basic` or `harbour`.

## Endpoints

### POST `/tables` (create)
- **Body:** `{ name?, is_public?, password?, version? }`
  - `version` optional; `"basic"` | `"harbour"`. Anything else (or omitted) →
    stored as `harbour`.
- **Response:** `{ code }` (unchanged).

### GET `/tables` (list) and GET `/tables/{code}` (detail)
- **Response now includes:** `game_version` (string, `"basic"` | `"harbour"`).
  Use it to render the version label/badge on the lobby and table list.

### Game state (WebSocket `state_update`)
- `state.version` holds the **display name** (`"Basic"` | `"Harbour"`), not the
  key. Safe to show directly; do **not** send it back to the create endpoint —
  send the lowercase key there.

## Frontend to-do (B5)
- Create panel: a version selector (Basic / Harbour) → send `version` as the
  lowercase key. Default the control to Harbour to match server default.
- List + lobby: show the version from `game_version`. Degrade gracefully if the
  field is absent (older API / cached response) — treat missing as Harbour.

## Backend notes (done in B4)
- `game_version` column added to `wp_mk_tables`
  (`VARCHAR(16) NOT NULL DEFAULT 'harbour'`), via an explicit idempotent
  migration (`mk_migrate()`); existing rows backfill to `harbour`.
- `websocket-server` maps version → `GameConfig` with `config_for_version()`
  (`game_config.py`) at both `create_initial_state` call sites (initial build
  and rematch). Unknown/missing → Harbour.
- A rematch keeps the table's version (read from `state.version`).

## Not yet exercised live
- The DB round-trip (PHP writes `game_version` → websocket-server reads it on
  game start) is wired and unit/smoke-tested at the engine level, but has **not**
  been run against a live MySQL instance locally (no DB/stack available in the
  dev box). CI-1 adds a MySQL service container that will exercise the migration
  and bootstrap on every push.
