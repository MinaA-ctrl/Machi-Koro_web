# Migration Discipline (DOC-1 / retro action #4)

> Schema changes (`wp-plugin/machi-koro/includes/db.php`) take effect only on
> redeploy, and the obvious WordPress tool — `dbDelta` — does **not** do what its
> name implies for tables that already hold data. This note is the standing rule.

## The trap

`dbDelta` is reliable for **creating** tables, but on an **existing** table it
silently skips changes:

- It **does not add a column** reliably when the `CREATE TABLE` text changes —
  it parses loosely and no-ops on many diffs.
- It **does not add a UNIQUE index** if existing rows already violate it
  (this bit QA-001 in Sprint 1).
- It gives **no error** when it skips — the code looks correct, the column is
  absent, and you only find out in a manual staging sweep (the DEPLOY-001
  near-miss).

So: code being correct is **not** sufficient. A migration must actually run, and
be verified, against a real MySQL.

## The rule

1. **Fresh installs:** keep the full schema in the `dbDelta` `CREATE TABLE` in
   `mk_install()`. That path is fine for brand-new tables.

2. **Any change to an existing table** (add/alter column, add/change index) goes
   in `mk_migrate()` as an **explicit, idempotent, guarded `ALTER`**:
   - Guard on `information_schema` (or `SHOW COLUMNS`/`SHOW INDEX`) so re-running
     is a no-op.
   - Never rely on `dbDelta` to apply it.

   ```php
   $has = $wpdb->get_var($wpdb->prepare(
       "SELECT COUNT(*) FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = 'game_version'",
       DB_NAME, "{$wpdb->prefix}mk_tables"
   ));
   if (!$has) {
       $wpdb->query("ALTER TABLE {$wpdb->prefix}mk_tables
           ADD COLUMN game_version VARCHAR(16) NOT NULL DEFAULT 'harbour' AFTER name");
   }
   ```

3. **Make it reach live installs without a manual reactivation.** `mk_migrate()`
   runs both from `mk_install()` (activation) and from `mk_maybe_migrate()` on
   `plugins_loaded`, gated by the `mk_db_version` option vs. the `MK_DB_VERSION`
   constant. **Bump `MK_DB_VERSION` whenever you add a migration** — that bump is
   what triggers the run on deployed sites.

4. **Verify against MySQL, not by eye.** `SHOW COLUMNS FROM …` / `SHOW INDEX
   FROM …` must show the change. CI (`.github/workflows/php-ci.yml`, the
   `migration` job) now does exactly this on every push: it boots WordPress on a
   MySQL service, activates the plugin, and asserts the column exists on both a
   fresh install and a simulated pre-migration table. Backfill defaults so
   existing rows keep current behavior (e.g. `game_version DEFAULT 'harbour'`).
   The gates are proven to fail red on bad input (negative test, CI-1 AC):
   see [`ci-1-gate-proof.md`](./ci-1-gate-proof.md).

5. **UNIQUE index caveat:** before adding a UNIQUE key, de-dupe first
   (`SELECT … GROUP BY … HAVING COUNT(*) > 1`) or the `ALTER` fails on existing
   duplicates. MVP data is disposable — drop/recreate is acceptable there.

## Checklist when you touch a table

- [ ] Fresh-install DDL updated in `mk_install()` `CREATE TABLE`.
- [ ] Guarded idempotent `ALTER` added to `mk_migrate()`.
- [ ] `MK_DB_VERSION` bumped.
- [ ] Sensible `DEFAULT` so existing rows backfill safely.
- [ ] Verified with `SHOW COLUMNS` / `SHOW INDEX` (CI does this; do it on staging too).
- [ ] `deploy-checklist.md` item added if a staging action is still required.
