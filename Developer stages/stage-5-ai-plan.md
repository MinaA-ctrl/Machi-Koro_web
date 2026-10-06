# Stage 5: AI opponents trained by self-play

## Context
The roadmap (`README_1.md` ~:322, `MachiKoro_PRD.md:104`) has Stage 5 as "AI opponent (Easy/Medium/Hard)". The user wants bots that learn by playing against each other thousands of times (**reinforcement learning with self-play**, not unsupervised learning). They'll learn ML along the way and want to play-test the bots themselves.

**What's already in the code:**
- The rules engine `websocket-server/machi_koro_engine/` is plain Python with no server or database dependencies, so it can run headless and fast.
- `handle_action(state, seat, msg)` (`game_engine.py:583`) is the single entry point for moves.
- `build_prompt_payload` (:950) lists the options for every prompt.
- `default_response` (:1051) returns a safe default move.

**What's missing:**
- The dice RNG is one global shared by all games (`game_engine.py:16–24`).
- There's no `legal_actions()` for the roll and build phases.
- There's no bot concept anywhere.

**Decisions so far:**
- Training runs on the user's Mac, CPU only, limited to 1–2 cores, in the background, saving progress so it can be stopped and resumed. Nothing trains on the game server.
- Start with the **Base game, 2 players**; expand later.
- The user tests with a **text (terminal) game** from Phase A onward; browser integration comes in Phase F.
- Human games are used for **testing**, not as the main training signal.
- Security concerns will be discussed next and added to this plan.

**How we work:** one phase at a time. Each phase starts with a plain-language explanation of the new idea. A phase is finished only when every test on its "Done when" list passes and the user has play-tested it. Lessons go into a learning journal in `Developer stages/stage-5-ai-plan.md`.

---

## Phase 0: Urgent security fixes
**Goal:** close the security holes in the existing site that matter now or that the bots depend on, before any AI work starts.
**How and Done when:** see the table in section S5 below (items 1–5). Existing backend tests must also still pass.

---

## Phase A: Practice table, simple bots, text game
**Goal:** run full Machi Koro games headless and fast, and have two hand-written bots (Random and Simple) that the user can play against in the terminal. No AI learning yet.

**How:**
1. **Per-game dice.**
   - `create_initial_state` (`game_engine.py:31`) takes an optional `rng` and stores it with the game, and `roll_die` uses it.
   - The old global stays as a fallback, so the website and the existing tests behave exactly as before.
2. **"What can I do right now?" helper.**
   - New `machi_koro_engine/legal.py` with `legal_actions(state, seat)`. It returns every valid move for the current phase:
     - Roll phase: 1 die, or 2 dice with Train Station.
     - Build phase: affordable cards still in supply (Purple cards max 1 each), unbuilt landmarks, and "build nothing".
     - Prompt phases: reuse the options from `build_prompt_payload`.
3. **Bot interface and two bots** in a new package `websocket-server/machi_koro_ai/`.
   - `bots/base.py` defines one question every bot answers: `choose(state, seat, legal_moves) -> move`.
   - `RandomBot` picks a random legal move.
   - `SimpleBot` follows hand-written beginner strategy:
     - cheap income cards early
     - then landmarks
     - 2 dice once it has Train Station and cards for 7+
4. **`simulate.py`** runs N bot-vs-bot games with fixed dice seeds and prints win rates, average game length, and games per second.
5. **`play.py`** is the text game: the user against any bot.
   - Prints the board, shows the legal moves as a numbered menu, and asks again on invalid input.
   - The bot's moves are printed with a short pause.
   - Each game is saved to `machi_koro_ai/human_games/<date>_<n>.json` as a seed plus a list of moves.
   - `--replay <file>` replays a saved game step by step.

**Done when:**

| Area | Test |
|---|---|
| No regressions | All ~200 existing engine tests pass (`cd websocket-server && python3 -m pytest`) |
| Repeatability | Same seed and same moves give an identical final state, run twice |
| Isolation | Two games running side by side with different seeds don't affect each other's dice |
| Legal moves correct | Every move `legal_actions` returns is accepted by `handle_action` (it changes state, doesn't return `{}`), checked across 10,000 random games |
| Legal moves complete | Spot tests for each phase: e.g. 3 coins in the build phase gives exactly the expected list; no Train Station means no "roll 2" option; Purple card already owned means it isn't offered |
| No stuck games | 10,000 Random-vs-Random games all finish with a winner, under a turn cap of 500 |
| Bot strength | SimpleBot beats RandomBot ≥ 90% over 1,000 seeded games |
| Speed | Games/second measured and recorded (used to estimate training time in Phase C) |
| Text game | User plays at least 3 full games against SimpleBot; menus make sense, invalid input is handled, games save and replay correctly |

**Result:** **Easy** bot candidate (SimpleBot) plus the text game.

---

## Phase B: Turning the game into numbers
**Goal:** describe the game in the standard format AI learning tools understand: what the bot sees (numbers), what it can do (a fixed numbered menu), and how it's scored (win/loss).

**How:**
1. `encoding.py`:
   - **Board → numbers:** a fixed-length list containing:
     - own coins, card counts per type, and landmarks as 0/1
     - the same for the opponent
     - supply counts
     - current phase
     - last roll
   - **Moves → menu:** a fixed numbered list of every move that could ever exist in the Base game (~40). There are two-way converters: menu number ↔ engine move.
   - **Mask:** a 0/1 flag for each menu item, built from `legal_actions`, so only allowed moves can be picked.
2. `env.py` is a Gymnasium environment:
   - The learner plays one seat, and an opponent bot plays inside `step()`.
   - Reward is +1 win and −1 loss.
   - An optional small bonus per landmark is switched off by default, kept for experiments.

**Done when:**

| Area | Test |
|---|---|
| Round trip | For every legal move in 1,000 random games: move → menu number → move gives the same move back |
| Mask matches rules | In 1,000 random games, the menu items marked allowed are exactly the moves `legal_actions` returns |
| Fixed size | The numbers list is always the same length and contains no invalid values (no NaN, no negatives where impossible) |
| Standard check | Gymnasium's built-in `check_env` passes |
| Sanity | A random agent inside the env gets the same win rate vs RandomBot as in Phase A (~50% ± a few %) |
| Rewards | Wins give +1, losses −1, and nothing else unless the bonus is switched on |

**Result:** no new bot yet; the game is now "trainable".

---

## Phase C: First trained bot
**Goal:** a bot that learns from its own wins and losses and beats SimpleBot, showing that the learning works.

**How:**
1. AI tools go in a separate `requirements-ai.txt` (`torch`, `gymnasium`, `sb3-contrib` for MaskablePPO, `tensorboard`), so the game server stays unchanged.
2. `train.py`:
   - trains against RandomBot first, then SimpleBot
   - limited to 1–2 CPU threads
   - saves a checkpoint every N steps to `machi_koro_ai/checkpoints/` and can resume from one
   - logs a live win-rate chart (TensorBoard)
3. `TrainedBot` loads a checkpoint, so `simulate.py` and `play.py` can use it (`--opponent trained-<name>`).

**Done when:**

| Area | Test |
|---|---|
| Learning happens | Win-rate chart climbs over training, not flat |
| Beats random | Trained bot vs RandomBot ≥ 90% over 1,000 seeded games |
| Beats simple | Trained bot vs SimpleBot ≥ 55% over 2,000 seeded games (2,000 because dice luck is noisy) |
| Never cheats | 0 illegal moves attempted across all evaluation games |
| Resume works | Stopping training and resuming from a checkpoint continues the curve instead of restarting |
| Laptop friendly | Training uses no more than the configured cores; the Mac stays usable |
| Human test | User plays ≥ 5 games in the text game and notes in the journal what the bot does well or oddly |

**Result:** **Medium** bot candidate.

---

## Phase D: Self-play
**Goal:** the bot improves by playing copies of itself, past and present, until it's clearly stronger than anything hand-written. Then the approach expands to more players and expansions.

**How:**
1. **Opponent pool:** each training game picks its opponent from a mix of:
   - past checkpoints
   - the latest version
   - SimpleBot and RandomBot

   The old opponents stop it from forgetting how to beat simple styles.
2. `evaluate.py` runs a round-robin tournament between checkpoints and computes **Elo ratings**, the chess-style strength score.
3. Expand one step at a time, retraining for each and repeating the tests:
   - Harbour
   - 3–4 players
   - Sharp
4. If the user found a weakness while play-testing, add a scripted opponent that exploits it to the pool.

**Done when:**

| Area | Test |
|---|---|
| Steady improvement | Elo increases across checkpoints (later versions beat earlier ones) |
| No forgetting | The latest version still beats SimpleBot ≥ 55% and RandomBot ≥ 90% |
| Clearly stronger | The best self-play bot beats the Phase C bot ≥ 55% over 2,000 games |
| Expansions | For each new mode: the Phase A legal-move and no-stuck-game tests pass, and the bot beats SimpleBot in that mode |
| Human test | User plays ≥ 5 games; weaknesses noted from earlier play-tests are gone or reduced |

**Result:** **Hard** bot candidate.

---

## Phase E: Difficulty levels
**Goal:** three levels that *feel* right to a human: Easy is fun, Medium is a fair fight, and Hard is a real challenge.

**How:**
- **Easy:** SimpleBot, or an early checkpoint with some random moves mixed in.
- **Medium:** a mid-strength checkpoint that sometimes picks its 2nd-best move.
- **Hard:** the best checkpoint, always picking its best move.
- Choose them so each level is clearly stronger than the one below (~150–200 Elo apart).

**Done when:**

| Area | Test |
|---|---|
| Ordered strength | Hard beats Medium ≥ 60%, Medium beats Easy ≥ 60% (2,000 games each) |
| Human feel | User plays ≥ 3 games per level; the journal confirms the levels feel distinct and Easy is still fun |

---

## Phase F: Bots in the real website
**Goal:** a host can add Easy, Medium or Hard bots to a table and play them in the browser.

**How:**
1. **Running the bot:** export it to ONNX and run it with `onnxruntime` on the server, which is lightweight, so there's no training code on the server. `machi_koro_ai/runtime.py` has `BotPlayer(level).choose(state, seat)`.
2. **Database:** add `is_bot` and `bot_level` to `Player` (`persistence/models.py:136`), with Alembic migration 0008.
3. **Tables API** (`app/routers/tables.py`): the host can add or remove a bot in an empty seat. Bots count toward the minimum of 2 players. "Add bot" is shown only for game modes a bot was trained on.
4. **Game driver** (`app/ws.py`):
   - When it's a bot's turn or prompt, wait ~1 s, then make its move through the same path humans use.
   - This runs under the existing per-game lock.
5. **Frontend:**
   - an "Add bot" control in the waiting room
   - a bot badge on seats
   - EN/RU texts
6. **Stats:** bot games are tagged and kept out of human-vs-human stats.

**Done when:**

| Area | Test |
|---|---|
| No regressions | All existing backend tests pass (`app/tests`, `persistence/tests`) |
| New API tests | Only the host can add or remove bots; a bot can't be added to a full or started table; a table with 1 human + 1 bot can start |
| Bot-driven game | Automated test: a game with only bots plays to the end through the real server code |
| Turn handling | The bot answers every prompt type (Radio Tower, TV Station, Business Center…) without hitting the 45 s timeout |
| Response time | A bot's move takes < 50 ms to compute (excluding the deliberate delay) |
| Browser | User creates a table, adds a Hard bot, and plays a full game; the bot moves on its own, the game ends properly, and stats are tagged |

---

## Human play-testing (all phases)
- From Phase A, `play.py` lets the user play any bot or checkpoint in the terminal.
- Play-test after A, C, D and E (the minimum game counts are in each phase's "Done when").
- Every human game is saved to `machi_koro_ai/human_games/`. Uses:
  - spotting weaknesses
  - replaying games
  - possibly imitation learning ("a bot that plays like the user") later, if enough games pile up
- Human games are **not** the main training source; there are far too few.

## Security & privacy

### S1. The user's Mac during training
- Install the AI libraries only from the official Python package index (PyPI), inside a **separate virtual environment** (`.venv-ai`), with exact versions pinned in `requirements-ai.txt`. Nothing is installed system-wide, and deleting that folder removes it all.
- **Never load model files from strangers.** PyTorch checkpoint files can run code when opened. We only load checkpoints we trained ourselves, with `torch.load(..., weights_only=True)`.
- Training needs no internet and no access to the database, and uses no personal data: it's just bots playing bots.
- CPU is limited to 1–2 threads, and training can be stopped at any time.
- Test: `train.py` runs with the network off; the checkpoint loader rejects a non-weights file.

### S2. Bots must not cheat
- The bot sees only what a human player can see. Its observation is built from public information only, and **never the hidden deck order**.
- Every bot move goes through the same `handle_action` rule checks as a human's. The bot can't act out of turn or make a move a human couldn't.
- The bot driver runs under the same per-game lock, so there are no race conditions.
- Tests:
  - an encoding test proves the deck order isn't in the observation (two states that differ only in deck order give identical observations)
  - bot-move tests check that out-of-turn and illegal moves are rejected

### S3. Game server safety (Phase F)
- The model is shipped as **ONNX**, a pure-numbers format that can't run code. It's loaded from a fixed file included in the deploy, and there's never an upload endpoint for models.
- **Limits:**
  - at least 1 human per table
  - at most `max_players − 1` bots
  - only the host can add or remove bots
  - adding a bot uses the existing `create_limit` rate limit
- When all humans disconnect, the bot stops playing and the table goes to the existing reaper.
- Each bot move has a timeout (e.g. 200 ms). If it's exceeded, the move falls back to `default_response` (`game_engine.py:1051`), so a broken model can't freeze a game.
- Tests:
  - API tests for each limit
  - a table can't be started with bots only
  - a timeout test with a deliberately slow bot
  - a load test: 50 bot tables at once while server response time stays normal

### S4. Data & privacy for AI work
- The user's text games are saved **only on the Mac** in `machi_koro_ai/human_games/`. That folder and `checkpoints/` are **gitignored**, so they're never pushed to GitHub.
- **Real players' games from the website are NOT used for training.** If that's ever wanted, it needs a privacy policy that mentions it, consent, and the data stripped of names and `user_id` first.
- Bot games are tagged in the `Score` table so they're kept out of human stats.

### S5. Existing website issues found during the review (outside the AI work)
These are already in the live code. The urgent ones become **Phase 0**, done before Phase A. The rest form a separate privacy track.

**Phase 0: fix before starting the AI work**

| # | Issue | Why it matters | Fix | Test |
|---|---|---|---|---|
| 1 | Lobby WebSocket has no authentication (`app/ws.py:279–305`) | Anyone who knows a table code can fake "player kicked" messages, or close the table by connecting as seat 0 | Require the same seat token as the game socket; ignore any `seat` value the client sends | Connecting without a token is refused; a non-host can't fake a kick or close the table |
| 2 | Hidden deck order is sent to every player (`game_engine.py:66–121`, broadcast `ws.py:62–74`) | In Variable Supply games, a technical player can see upcoming market cards. It's a cheat, and the bot rule in S2 needs it fixed anyway | Send only the deck **count** to clients (the frontend `Market.tsx:43` only checks whether a deck exists) | A broadcast state contains no deck list; Market UI still works |
| 3 | Old `.env` with real MySQL passwords is in git history (commit `bb9dc16`) | The repo is **public**, and the current `.env` still uses those same MySQL passwords. MySQL is **live** (WordPress) | Change the MySQL passwords on the server (inside MySQL, not only in `.env`). Change the weak Postgres password too. Scrubbing the history is optional once they're changed | User confirms the passwords were changed |
| 4 | Postgres runs on public port 5433, with a weak default password if `.env` doesn't set one (`docker-compose.yml:26–30,65`) | The database could be reachable from the internet | Remove the public port mapping (or bind it to 127.0.0.1); require `POSTGRES_PASSWORD` with no default | Port not reachable from outside the server; compose fails without a password |
| 5 | No size or parse checks on WebSocket messages (`ws.py:440–443`) | A huge or broken message could crash a connection or fill memory | Cap message size, catch bad JSON, whitelist reaction emojis | Tests with oversized and malformed messages |

**Privacy track (separate from Stage 5; it can run alongside)**
- **No privacy policy or terms page.** The site stores emails, password hashes and game history, so a policy is needed. Depending on where players live, laws like the EU's GDPR or Russia's personal-data law (152-FZ) may apply. Get proper legal advice for the final text.
- **No way to delete an account.** Add "delete my account", which removes the user row and either anonymizes or deletes their scores (`Score.user_id` has no foreign key today, so this needs explicit handling).
- **Guest accounts and scores are kept forever.** Add a cleanup job for old guest accounts.
- **Login tokens are in localStorage** (`frontend/src/lib/tokens.ts`). Any XSS bug could steal them. Consider moving to httpOnly cookies.
- **Refresh tokens can't be revoked.** Add token rotation and revocation, which also enables "log out everywhere".
- **Rate limits are missing** on join, refresh and WebSocket messages, and the IP can be spoofed via the `X-Real-IP` header when the backend is reached directly.
- **nginx has no HTTPS config or security headers.** Confirm TLS is handled in front of nginx in production, and add security headers (CSP, HSTS, X-Frame-Options).
- **Seat token is sent in the URL** (`?token=`), so it can end up in proxy logs. Medium priority.

## Critical files
- **Modify:**
  - `websocket-server/machi_koro_engine/game_engine.py` (RNG :16–24, `create_initial_state` :31)
  - `persistence/models.py`
  - `app/ws.py`
  - `app/routers/tables.py`
  - frontend waiting-room and seat components
- **New:**
  - `machi_koro_engine/legal.py` and its tests
  - `websocket-server/machi_koro_ai/`: `bots/`, `encoding.py`, `env.py`, `simulate.py`, `play.py`, `train.py`, `evaluate.py`, `runtime.py`, `checkpoints/`, `human_games/`, `tests/`
  - `requirements-ai.txt`
  - `Developer stages/stage-5-ai-plan.md` (this plan plus the learning journal)

---

## Learning journal

*(One entry per phase: what we built, what it taught, play-test notes.)*

### Phase 0 — security fixes (2026-10-05)
Done in code (all tests pass: engine 203, app 51, persistence 8):
- **#1 Lobby socket auth.** The lobby now requires the per-seat token, and the token's identity must still own the seat in the DB. This check was added to the game socket too, so a kicked player's leftover token is dead everywhere. Clients can only send `player_kicked`/`game_started` (host only) and `player_renamed`, and the server stamps the sender's seat. A replaced socket (reload or second tab) no longer closes the table.
- **#2 Deck order hidden.** `public_state()` sends `deck_count` instead of `deck`.
- **#4 Postgres** is bound to 127.0.0.1 and compose refuses to start without `POSTGRES_PASSWORD`.
- **#5 Message checks:**
  - 4 KB per-frame cap, plus `--ws-max-size 65536` on uvicorn
  - bad JSON is ignored
  - reaction emojis are whitelisted
  - a crashing action is logged instead of dropping the socket
  - the engine rejects non-string build ids
- Fixed a stale test (`test_per_seat_ws_auth_on_jwt_identity`).

Waiting on the user: **#3**, changing the MySQL passwords (they're leaked in a public repo) and the weak Postgres password on the server.

Lesson: the order of WS broadcasts matters in tests, because a sender receives its own broadcast too.

**Server check (2026-10-05):**
- Production runs Caddy, frontend, backend and Postgres. There's no MySQL or WordPress.
- Postgres is not published to the host (internal port only) and isn't using the default password.
- So the leaked MySQL passwords and #4 don't affect production; they only affect the local legacy setup. The rotation script (`scripts/rotate-db-passwords.sh`) is kept for later use.
- The server folder is not a git checkout, and its config files (`Caddyfile`, `docker-compose.override.yml`, `docker-compose.legacy.yml`, `site/`) aren't in the repo. Follow-ups:
  - bring the server config into git
  - deploy the Phase 0 code (backend and frontend together)
