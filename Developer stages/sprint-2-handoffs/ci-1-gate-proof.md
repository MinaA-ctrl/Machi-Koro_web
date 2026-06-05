# CI-1 / TASK-108 — Gate Proof (negative test)

Closes the last open AC on **CI-1**: proof that the `php-ci` gates go **red on bad
input**, not just green on good. The workflow (`.github/workflows/php-ci.yml`) had
never run; this is a one-time intentional-break check.

- **Repo:** `MinaA-ctrl/Machi-Koro_web`
- **How:** all work done on a throwaway branch `ci-1-gate-proof` in an isolated
  git worktree, snapshotting the current working-tree plugin + `php-ci.yml` only.
  Nothing was committed to the working branch (`stage-0-and-0.5`); the scratch
  branch was deleted after. None of the breakage landed on the working branch.
- **Date:** 2026-06-05

## Results

| # | Scenario | php-lint | migration | Run |
|---|----------|----------|-----------|-----|
| 1 | **Baseline** (good input) | ✅ pass | ✅ pass | [27018539527](https://github.com/MinaA-ctrl/Machi-Koro_web/actions/runs/27018539527) 🟢 |
| 2 | **php-lint break** — syntax error in `includes/db.php` | ❌ **fail** | ❌ fail¹ | [27018623613](https://github.com/MinaA-ctrl/Machi-Koro_web/actions/runs/27018623613) 🔴 |
| 3 | **migration break** — `mk_migrate()` neutered to no-op | ✅ pass | ❌ **fail** | [27018750725](https://github.com/MinaA-ctrl/Machi-Koro_web/actions/runs/27018750725) 🔴 |
| 4 | **fresh-install break** — `game_version` removed from `CREATE` | ✅ pass | ❌ **fail** | [27018854652](https://github.com/MinaA-ctrl/Machi-Koro_web/actions/runs/27018854652) 🔴 |
| 5 | **Revert all** → back to baseline | ✅ pass | ✅ pass | [27018925878](https://github.com/MinaA-ctrl/Machi-Koro_web/actions/runs/27018925878) 🟢 |

¹ The migration job also fails in #2 as expected collateral — a syntax error in a
loaded plugin file breaks `wp plugin activate` too. The php-lint gate is the one
under test here.

## Evidence per gate

### 1. php-lint gate (run 27018623613, 🔴)
The `php -l across all plugin PHP files` step **names the offending file**:
```
PHP Parse error:  syntax error, unexpected token "{", expecting variable in
    wp-plugin/machi-koro/includes/db.php on line 107
Errors parsing wp-plugin/machi-koro/includes/db.php
xargs: php: exited with status 255; aborting
##[error]Process completed with exit code 124.
```
→ A syntax error in any plugin file turns the gate red and points at the file.

### 2. migration gate — "restored on existing table" (run 27018750725, 🔴)
`mk_migrate()` was made a no-op, so the dropped column is not re-added. Step
conclusions for the `migration` job:
```
success   Activate plugin (runs mk_install bootstrap)
success   Fresh install has game_version           ← CREATE still has the column
failure   Migration restores game_version on a pre-B4 table
```
The step drops `game_version`, deletes `mk_db_version`, runs `mk_migrate()`, then
`SHOW COLUMNS … | grep -q game_version` — which exits non-zero because the column
was never restored. This is exactly the dbDelta blind spot (retro #4) the gate
exists to catch. `php-lint` stayed green, so the gate is cleanly isolated.

### 3. fresh-install assertion (run 27018854652, 🔴) — optional check
`game_version` removed from the `dbDelta` `CREATE TABLE` (with `mk_migrate` still
neutered so it can't backfill):
```
failure   Fresh install has game_version
skipped   Migration restores game_version on a pre-B4 table   ← job stops on first failure
```
→ If the column is missing from the fresh-install schema, the gate goes red too.

## Conclusion
All three assertions in `php-ci.yml` fail red on the corresponding bad input and
return green when reverted (run 27018925878). The gates are real, not green-only.
**CI-1 AC satisfied.** Scratch branch `ci-1-gate-proof` deleted; no breakage on
`stage-0-and-0.5`.

> Note: workflow runs surface a non-blocking annotation that `actions/checkout@v4`
> uses Node 20 (deprecated; forced to Node 24 from 2026-06-16). Cosmetic for now —
> bump to a Node-24 checkout when convenient. Not a gate failure.
