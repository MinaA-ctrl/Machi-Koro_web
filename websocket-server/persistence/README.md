# persistence — Postgres game-data layer (Stage 2, S2.2)

Async SQLAlchemy 2.0 + asyncpg models, repository functions, and Alembic
migrations for the new FastAPI backend. **Parallel build — DORMANT.** The live MVP
keeps running on WordPress + MySQL (`main.py`'s aiomysql code is untouched); this
layer is wired in at the S2.6/S2.7 cutover. Built and CI-tested against Postgres now
so the cutover is a drop-in swap.

## Layout
```
persistence/
├── database.py     # env-driven async engine + async_sessionmaker
├── models.py       # SQLAlchemy 2.0 models: Table, Player, GameState, Score
├── repository.py   # get_table / load_state / save_state / save_scores
├── alembic.ini     # script_location = %(here)s/migrations; URL from env (NOT in ini)
├── migrations/     # Alembic env (async) + versions/0001_baseline.py
├── pytest.ini      # backend suite config (asyncio_mode=auto, pythonpath=..)
└── tests/          # persistence suite (needs a live Postgres)
```

## Config (env)
`DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD` → an `postgresql+asyncpg://…` URL,
or a full `DATABASE_URL` override (driver auto-normalized). Same env the live
aiomysql code reads (`DB_*`), pointed at Postgres.

## Models (mirror the live `wp_mk_*` schema + the flags)
- **tables** — `join_code`, `name`, `game_version`, `sharp`, `variable_supply`,
  `password_hash`, `creator_id`, `is_public`, `status` (waiting/playing/finished),
  `max_players`, `created_at`, `finished_at`.
- **players** — `table_id` (FK, cascade), `seat`, `display_name`, `user_id`
  (NULL = guest), `is_host`, `joined_at`. `UNIQUE(table_id, seat)`.
- **game_states** — `table_id` (FK, **UNIQUE** — one current state per table),
  `state` (**JSONB**), `game_seq`, `updated_at`.
- **scores** — `table_id` (FK), `user_id`, `game_seq`, `landmarks_built`,
  `coins_at_end`, `won`, `played_at`. `UNIQUE(table_id, game_seq, user_id)`.

> Users / entitlements / wallet are **not** here — they arrive as their own Alembic
> migrations in S2.4 / S2.5.

## Repository (drop-in for the game loop, session-injected)
- `get_table(session, join_code) -> Table | None` — the version/sharp/variable_supply flags.
- `load_state(session, join_code) -> dict | None` — the persisted engine state.
- `save_state(session, join_code, state) -> bool` — per-action upsert of the one
  `game_states` row (restart-safe).
- `save_scores(session, join_code, state) -> int` — atomic upsert of registered
  players' results on `(table_id, game_seq, user_id)` (guests skipped; idempotent
  re-finish; rematch-safe). Table/player writes (create/join) land with S2.3's REST.

The functions take an **`AsyncSession`** (not a bare `code`): the FastAPI layer
injects one via `Depends`, and the cutover can wrap a turn's `save_state` +
`save_scores` in a single transaction. Tests inject a test session.

## Migrations
Run from this directory (URL comes from env):
```
cd websocket-server/persistence
alembic upgrade head            # apply baseline
alembic revision --autogenerate -m "msg"   # author the next migration (S2.4/S2.5…)
```

## Tests
Need a live Postgres with the baseline applied (CI's `backend-tests` job boots a
Postgres service, runs `alembic upgrade head`, then):
```
cd websocket-server/persistence && python -m pytest
```
Covers: schema-present-after-migration, state round-trip / restart-survival,
per-action upsert, and scores rematch-safety (the UNIQUE key).
