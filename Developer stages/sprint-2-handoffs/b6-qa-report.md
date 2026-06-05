# B6 — Live QA Report (Basic / Harbour version support)

**Finder:** QA · **Date:** 2026-06-05 · **Sprint:** 2 (Stage 1, Base-game-first)
**Scope:** B4 (backend version support) + B5 (frontend version selector & labels), end-to-end on the live stack.

## Environment
- Full Docker stack via `docker-compose.yml`: `db` (mysql:8.0), `wordpress`, `websocket` (FastAPI/uvicorn), `nginx` (`:8082`).
- `.env` already populated; `MK_WS_SECRET` is fed as the same `${MK_WS_SECRET}` to both `wordpress` and `websocket` — shared-secret requirement satisfied (game WS auth worked, no 4401s).
- **WP plugin** (`wp-plugin/machi-koro`) is **bind-mounted** → B5 frontend ships without a rebuild.
- **websocket** is a **built image** (`build: ./websocket-server`) → B4 engine code ships **only after `docker compose build websocket`**. See **QA-008** below — the running image was stale (pre-B4) and had to be rebuilt before any Basic behavior was correct.

## Method
Drove the **real** REST + WebSocket flow through nginx, exactly as the browser does (anonymous guest create → join → start → game WS with the HMAC seat token). A two-player economy bot played real games to natural winners. Frontend (B5) verified by confirming the served assets/markup are live and that the data values feeding the badges are correct. Driver: `/tmp/mkqa/driver.py` (scenarios: `content`, `play`, `fallback`, `persist_setup/verify`).

---

## Results — one line per checklist item

### 1. Basic happy path → **PASS**
Created a Basic table, bot-played to a natural winner. Winner built **exactly the 4 base landmarks** — `train_station, shopping_mall, amusement_park, radio_tower` — and victory triggered (`phase=finished`, `winner=seat 0`, 4 landmarks built, scoreboard emitted). No errors; game state `version="Basic"`.
- **Repro:** Front page → Create → select **Basic** → Create Public; second client joins via code; host Starts; play until a player builds all 4 landmarks → game ends with that player as winner. (Evidence run: table `MK-0354F1`, 462 WS msgs, winner landmarks `[train_station, shopping_mall, amusement_park, radio_tower]`.)

### 2. Basic content integrity → **PASS**
Basic game supply/market = **exactly the 15 base cards**; all 10 excluded cards absent; landmark set = the 4 base only (no City Hall/Harbor/Airport).
- Supply (15): `apple_orchard, bakery, business_center, cafe, cheese_factory, convenience_store, family_restaurant, farmers_market, forest, furniture_factory, mine, ranch, stadium, tv_station, wheat_field`.
- Absent as required: `flower_garden, mackerel_boat, tuna_boat, sushi_bar, hamburger_stand, pizza_joint, flower_shop, food_warehouse, publisher, tax_office`; landmarks absent: `city_hall, harbor, airport`.
- **Repro:** Create a Basic table, start, open the game; inspect the market/supply and landmark column. (Evidence: table `MK-08F4AD`, `supply_count=15`, `excluded_cards_present=[]`, `excluded_lms_present=[]`.)

### 3. City Hall net — absent in Basic, present in Harbour → **PASS**
Exact inverse signatures across a full Basic game and a full Harbour game:
- **Basic:** `+1 City Hall` coin-events = **0**; observed **172** turns where the active player entered Build at **0 coins** after a no-income roll and **stayed at 0** (samples: seat 0 roll 11; seat 1 roll 7; seat 0 roll 6).
- **Harbour:** `+1 City Hall` coin-events = **5**; **0** zero-at-build occurrences (the net bumps 0→1, so no one sits at 0).
- **Repro:** In a Basic game, get a player to 0 coins and roll a number matching none of their cards → coins stay 0, no "City Hall" toast. In Harbour, same situation → a `+1 City Hall` coin event fires.

### 4. Harbour regression → **PASS**
Harbour table builds the full set and plays as before: 25-card supply, all 7 landmarks incl. `city_hall/harbor/airport`, harbour-only cards present (`mackerel_boat, tuna_boat, sushi_bar, food_warehouse`). Bot-played to a natural **6-landmark win** (`city_hall` pre-built + the 6 buildable), City Hall net firing, no errors. `version="Harbour"`.
- **Repro:** Create → select **Harbour** (default) → play; full card set and Harbor mechanics behave as the pre-B4 live build. (Evidence: table `MK-452EAA`, winner 6 landmarks, 5 City-Hall events.)

### 5. Version label (B5) + persistence → **PASS**
- **Label/data path:** lobby `GET /tables/{code}` returns `game_version` (`"basic"`/`"harbour"`); in-game `state.version` is `"Basic"`/`"Harbour"`. Both correct live.
- **B5 markup/CSS served live** (plugin bind-mount): create-panel selector (`mk-version-select`, `data-version="basic|harbour"`) on the front page; lobby badge (`#mk-table-version`) on `/waiting-room/`; topbar badge (`#mk-game-version` / `mk-version-badge-topbar`) + drawer (`#mk-my-version`) on `/game/`. `app.js`/`style.css` contain the B5 code.
- **Persistence across WS restart:** mid-game `docker compose restart websocket`, then reconnected with the surviving seat token → state reloaded with `version="Basic"` and progress (`game_seq`, total coins, total cards) **identical** before/after; no crash. (Evidence: table `MK-FB9B97`.)
- **Residual (not blocking):** the badge **pixels** were not eyeballed in a GUI browser (no interactive browser in this harness). All inputs to rendering are verified live: markup deployed, CSS deployed, JS rendering code deployed + syntax-valid, and the data values correct. Recommend a 30-second human glance at the lobby/game badge during the Stage-1 batch.

### 6. Fallback (missing / unknown version → Harbour) → **PASS**
- DB `game_version='sharp'` (unknown) → game loads as **Harbour**, no crash.
- DB `game_version=''` (empty) → loads as **Harbour**, no crash.
- **NULL is structurally impossible:** column is `VARCHAR(16) NOT NULL DEFAULT 'harbour'`, and the B4 migration adds it with that default, so legacy/missing rows are `'harbour'` by schema — `config_for_version()` then handles any other unknown string defensively.
- **Repro:** `UPDATE wp_mk_tables SET game_version='sharp' WHERE code=…;` then start/open the game → Harbour ruleset, no error. (Evidence: tables `MK-FBE29F`, `MK-C29402`.)

---

## Bug filed

### QA-008 · Deploy/Release · High · P1 · OPEN
**B4 does not reach the running stack on a plain `docker compose up -d` — the `websocket` image must be rebuilt.**

- **Severity rationale:** Symptom is silent and severe. Before I rebuilt, the **running websocket image was pre-B4** (built 2026-05-27; `game_config.py` added 2026-06-05). A **Basic** table then built a **full Harbour game** (25-card supply, all 7 landmarks incl. City Hall/Harbor/Airport) with **`state.version = null`**. The DB stored `game_version="basic"` correctly, but the engine ignored it. No error surfaced.
- **Root cause:** `websocket` is a built image (`build: ./websocket-server`), unlike the **bind-mounted** WP plugin. `docker compose up -d` reuses the cached image, so B4 Python changes don't ship until `docker compose build websocket`. The bind-mount asymmetry makes B5 (frontend) look deployed while B4 (engine) is not.
- **Environment:** Docker stack, `websocket` image dated before the B4 commit.
- **Steps to reproduce:**
  1. With a pre-B4 `websocket` image running, create a **Basic** table (DB `game_version="basic"`).
  2. Start + open the game; inspect state.
  3. **Actual:** full Harbour supply/landmarks; `state.version` is `null`. Basic ruleset absent.
  4. **Expected:** 15-card Base supply, 4 base landmarks, `state.version="Basic"`.
- **Fix / mitigation:** `docker compose build websocket && docker compose up -d websocket` (or `--build`). **Add "rebuild the `websocket` image" to the deploy checklist** for any sprint that changes `websocket-server/`. After rebuild, all of items 1–6 above PASS.
- **Status:** Mitigated in this environment by rebuilding before testing. The deploy-checklist gap remains until recorded there.

---

## Note to PM
- **Not a code defect in B4/B5** — both behave correctly once deployed. The risk is purely release-process: **QA-008** would let B4 ship "green in review" yet be silently absent in prod, with Basic tables playing as Harbour and a `null` version label. Please fold "rebuild `websocket` image when `websocket-server/` changes" into `deploy-checklist.md`.
- Did **not** commit (owner batches the Stage 1 commit). No source files changed by QA; the only stack change was rebuilding the `websocket` image and a `restart websocket` (persistence test). Test tables (`MK-*`) remain in the DB.
