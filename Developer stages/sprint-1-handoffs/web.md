# Handoff → Web Developer · Sprint 1 (Stage 0: Stabilization)

> Paste this into a `web-developer` Claude session. Code lives in `~/Programming projects/Vibe_coding/Claude_Antropic/Machi Koro project`.
> ⚠️ Stack note: this is the **current MVP**, built as a WordPress plugin with vanilla JS / jQuery — `wp-plugin/machi-koro/assets/app.js` and `wp-plugin/machi-koro/includes/shortcodes.php`. The React rebuild is **Stage 3**, not now. For this one task, match the existing app.js style — don't introduce React yet.

## Sprint goal (your part)
A small but real cameo: finish the **table-password UX** so protected tables are usable. Everything else this sprint is Backend/QA.

## TASK-006 (frontend half) — Table password UI (Should · ~1–2 SP)
**Context:** Backend is wiring password protection into the REST API (`create_table` stores a hashed password; `join_table` enforces it; listings expose an `is_protected` flag). You build the UI around it.

**Do:**
- **Create-table form:** add an optional "Password (optional)" field; send it to `POST /tables`.
- **Public table list:** show a 🔒 indicator on tables where `is_protected` is true.
- **Join flow:** when joining a protected table, prompt for the password and send it to `POST /tables/{code}/join`. On a 403 (wrong password), show a clear inline error and let them retry.
- Keep it consistent with the existing lobby UI in `app.js` / `shortcodes.php`.

**AC:**
- [ ] Create-table form has an optional password field
- [ ] Protected tables show 🔒 in the list
- [ ] Join prompts for password on protected tables; wrong password shows a clear, retryable error
- [ ] Matches existing lobby styling

## Dependency
- **Blocked by Backend TASK-006 (backend half)** — you need the API to accept a password on create, enforce it on join, and return `is_protected` in listings. Coordinate timing via PM; you can stub against the expected contract while waiting.

## Definition of Done
- [ ] Code written & reviewed
- [ ] Manually verified against the staging Docker stack (with QA's TC for TASK-006)
- [ ] No regressions to existing create/join lobby flows
